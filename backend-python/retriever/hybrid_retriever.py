import os
import time
from pathlib import Path
from threading import Lock

import psycopg2
import psycopg2.pool
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from rank_bm25 import BM25Okapi

load_dotenv(Path(__file__).resolve().parent.parent.parent /
            ".env", override=True)

from retriever.vehicle_boost import apply_vehicle_rrf_boost

_USE_FASTEMBED = os.getenv("USE_FASTEMBED", "False").lower() in ("true", "1")

if _USE_FASTEMBED:
    try:
        from fastembed import TextEmbedding
    except ImportError:
        _USE_FASTEMBED = False

if not _USE_FASTEMBED:
    from sentence_transformers import SentenceTransformer
    import torch
    # Peak efficiency: limit threads to 4 to prevent core-over-allocation thrashing
    torch.set_num_threads(min(4, os.cpu_count() or 2))

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "legal_chunks")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
FASTEMBED_EMBEDDING_MODEL = os.getenv(
    "FASTEMBED_EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
PG_CONN = os.getenv(
    "POSTGRES_URL",
    "postgresql://raguser:ragpass@localhost:5432/ragdb?sslmode=disable",
)


class HybridRetriever:
    def __init__(self) -> None:
        self.qdrant = QdrantClient(QDRANT_URL, timeout=30)
        if _USE_FASTEMBED:
            self.embedder = TextEmbedding(model_name=FASTEMBED_EMBEDDING_MODEL)
            self._embed = lambda text: list(
                self.embedder.embed([text]))[0].tolist()
        else:
            self.embedder = SentenceTransformer(EMBEDDING_MODEL)
            self._embed = lambda text: self.embedder.encode(text).tolist()

        self.pg_conn = PG_CONN

        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1, maxconn=5, dsn=PG_CONN
            )
            print("[Retriever] PG connection pool created (1–5 conns)")
        except Exception as e:
            print(
                f"[Retriever] Pool init failed, will use direct connect: {e}")
            self._pool = None

        self._bm25_cache: dict[str | None, tuple[list[str], BM25Okapi]] = {}
        self._bm25_lock = Lock()
        print("[Retriever] BM25 cache initialized")

    def search(
        self,
        query: str,
        top_k: int = 20,
        domain: str | None = None,
    ) -> list[dict]:
        from concurrent.futures import ThreadPoolExecutor

        n = max(top_k * 4, top_k)
        t0 = time.perf_counter()

        # Run dense + sparse concurrently — critical for cold-domain first queries
        # (e.g. hon_nhan first hit: Qdrant HNSW + BM25 build overlap instead of stacking)
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_dense  = pool.submit(self._dense_search,  query, n, domain)
            f_sparse = pool.submit(self._sparse_search, query, n, domain)
            dense  = f_dense.result()
            sparse = f_sparse.result()

        t1 = time.perf_counter()

        merged = self._merge_rrf(dense, sparse, n)
        if domain in (None, "giao_thong"):
            merged = apply_vehicle_rrf_boost(query, merged)
        result = self._dedupe_by_content(merged, top_k)
        t2 = time.perf_counter()

        print(
            f"[Retriever] parallel={t1-t0:.3f}s | "
            f"merge={t2-t1:.3f}s | total={t2-t0:.3f}s | "
            f"results={len(result)} domain={domain!r}"
        )
        return result

    @staticmethod
    def _dedupe_by_content(items: list[dict], limit: int) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for item in items:
            raw = (item.get("content") or "").strip()
            key = " ".join(raw.split())[:500]
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def _dense_search(
        self,
        query: str,
        top_k: int,
        domain: str | None = None,
    ) -> list[dict]:
        query_vector = self._embed(query)

        qdrant_filter = None
        if domain and domain not in ("small_talk", None):
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="domain",
                        match=MatchValue(value=domain),
                    )
                ]
            )

        try:
            resp = self.qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=top_k,
                with_payload=True,
                query_filter=qdrant_filter,
            )
            if qdrant_filter and not resp.points:
                print(
                    f"[Retriever] domain filter '{domain}' empty — returning []")
                return []
        except Exception:
            resp = self.qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )

        out = []
        for r in resp.points:
            payload = dict(r.payload) if r.payload else {}
            out.append({**payload, "dense_score": r.score, "id": str(r.id)})
        return out

    def _get_conn(self):
        if self._pool:
            return self._pool.getconn()
        return psycopg2.connect(self.pg_conn)

    def _put_conn(self, conn) -> None:
        if self._pool:
            self._pool.putconn(conn)
        else:
            conn.close()

    def _build_bm25(self, domain: str | None) -> tuple[list[str], BM25Okapi]:
        with self._bm25_lock:
            if domain in self._bm25_cache:
                return self._bm25_cache[domain]

            conn = self._get_conn()
            try:
                cur = conn.cursor()
                if domain and domain not in ("small_talk",):
                    cur.execute(
                        """
                        SELECT dc.id, dc.content
                        FROM document_chunks dc
                        LEFT JOIN legal_documents ld ON dc.document_id = ld.id
                        WHERE ld.domain = %s OR ld.domain IS NULL
                        """,
                        (domain,),
                    )
                else:
                    cur.execute("SELECT id, content FROM document_chunks")
                rows = cur.fetchall()
                cur.close()
            finally:
                self._put_conn(conn)

            if not rows:
                empty = ([], None)
                self._bm25_cache[domain] = empty
                return empty

            ids = [str(r[0]) for r in rows]
            corpus = [r[1].split() for r in rows]
            bm25 = BM25Okapi(corpus)
            result = (ids, bm25)
            self._bm25_cache[domain] = result
            print(
                f"[Retriever] BM25 built for domain={domain!r}: {len(ids)} chunks")
            return result

    def _sparse_search(
        self,
        query: str,
        top_k: int,
        domain: str | None = None,
    ) -> list[dict]:
        if domain not in self._bm25_cache:
            self._build_bm25(domain)

        ids, bm25 = self._bm25_cache.get(domain, ([], None))

        if not ids or bm25 is None:
            print(
                f"[Retriever] sparse: domain '{domain}' empty — returning []")
            return []

        query_tokens = query.split()
        scores = bm25.get_scores(query_tokens)
        top_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]
        return [
            {"id": ids[i], "sparse_score": float(scores[i])}
            for i in top_indices
        ]

    def _fetch_chunk(self, chunk_id: str) -> dict | None:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT dc.content, dc.article, dc.clause, ld.law_name, ld.document_code,
                       ld.law_type, ld.effective_date, ld.expiry_date, ld.id, dc.page_number, ld.file_path
                FROM document_chunks dc
                JOIN legal_documents ld ON dc.document_id = ld.id
                WHERE dc.id = %s
                """,
                (chunk_id,),
            )
            row = cur.fetchone()
            cur.close()
        finally:
            self._put_conn(conn)
        if not row:
            return None
        eff, exp = row[6], row[7]
        return {
            "content": row[0],
            "article": row[1],
            "clause": row[2],
            "law_name": row[3],
            "document_code": row[4],
            "law_type": row[5],
            "effective_date": str(eff) if eff is not None else None,
            "expiry_date": str(exp) if exp is not None else None,
            "document_id": str(row[8]),
            "page_number": row[9],
            "file_path": row[10],
        }

    def _merge_rrf(
        self,
        dense: list[dict],
        sparse: list[dict],
        top_k: int,
        k: int = 60,
    ) -> list[dict]:
        scores: dict[str, dict] = {}

        for rank, item in enumerate(dense):
            pid = str(item["id"])
            row = {x: y for x, y in item.items(
            ) if x not in ("dense_score", "id")}
            scores[pid] = {
                "row": row,
                "dense_score": item.get("dense_score"),
                "sparse_score": None,
                "rrf": 1.0 / (k + rank + 1),
            }

        for rank, item in enumerate(sparse):
            pid = str(item["id"])
            contrib = 1.0 / (k + rank + 1)
            if pid not in scores:
                fetched = self._fetch_chunk(pid)
                if fetched is None:
                    continue
                scores[pid] = {
                    "row": fetched,
                    "dense_score": None,
                    "sparse_score": item["sparse_score"],
                    "rrf": contrib,
                }
            else:
                scores[pid]["sparse_score"] = item["sparse_score"]
                scores[pid]["rrf"] += contrib

        ranked = sorted(scores.items(), key=lambda x: -x[1]["rrf"])[:top_k]
        out = []
        for pid, v in ranked:
            out.append(
                {
                    **v["row"],
                    "chunk_id": pid,
                    "dense_score": v["dense_score"],
                    "sparse_score": v["sparse_score"],
                    "rrf_score": v["rrf"],
                }
            )
        return out


_global_retriever = None


def get_retriever() -> HybridRetriever:
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = HybridRetriever()
    return _global_retriever
