import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=True)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "legal_chunks")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
PG_CONN = os.getenv(
    "POSTGRES_URL",
    "postgresql://raguser:ragpass@localhost:5432/ragdb",
)


class HybridRetriever:
    def __init__(self) -> None:
        self.qdrant = QdrantClient(QDRANT_URL)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        self.pg_conn = PG_CONN

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        # Lấy nhiều ứng viên hơn rồi dedupe — tránh trùng nội dung (re-ingest / chunk trùng)
        n = max(top_k * 4, top_k)
        dense = self._dense_search(query, n)
        sparse = self._sparse_search(query, n)
        merged = self._merge_rrf(dense, sparse, n)
        return self._dedupe_by_content(merged, top_k)

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

    def _dense_search(self, query: str, top_k: int) -> list[dict]:
        query_vector = self.embedder.encode(query).tolist()
        # qdrant-client >= 1.10: dùng query_points thay cho search()
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

    def _sparse_search(self, query: str, top_k: int) -> list[dict]:
        conn = psycopg2.connect(self.pg_conn)
        cur = conn.cursor()
        cur.execute("SELECT id, content FROM document_chunks")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return []

        ids = [str(r[0]) for r in rows]
        corpus = [r[1].split() for r in rows]
        bm25 = BM25Okapi(corpus)
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
        conn = psycopg2.connect(self.pg_conn)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT dc.content, dc.article, dc.clause, ld.law_name, ld.document_code,
                   ld.law_type, ld.effective_date, ld.expiry_date, ld.id
            FROM document_chunks dc
            JOIN legal_documents ld ON dc.document_id = ld.id
            WHERE dc.id = %s
            """,
            (chunk_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
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
            row = {x: y for x, y in item.items() if x not in ("dense_score", "id")}
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
