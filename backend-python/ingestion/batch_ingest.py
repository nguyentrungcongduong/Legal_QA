"""
ingestion/batch_ingest.py
=============================
Batch ingest toan bo data/raw/<domain>/*.pdf vao Qdrant + PostgreSQL.
Tu dong detect domain tu ten thu muc.

Cach chay:
    cd backend-python
    .venv\Scripts\python.exe ingestion/batch_ingest.py

Hay truyen --domain de chi ingest mot domain cu the:
    .venv\Scripts\python.exe ingestion/batch_ingest.py --domain dat_dai
    .venv\Scripts\python.exe ingestion/batch_ingest.py --domain giao_thong --force

Options:
    --domain DOMAIN   Chi ingest thu muc domain do (mac dinh: tat ca)
    --force           Re-ingest du da co trong DB (override)
    --dry-run         Chi liet ke file, khong ingest that
"""
import argparse
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

# Them path de import ingest module
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT.parent / ".env", override=True)

# ─── Config ───────────────────────────────────────────────────────────────────
QDRANT_URL      = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "legal_chunks")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
PG_CONN         = os.getenv("POSTGRES_URL", "postgresql://raguser:ragpass@localhost:5432/ragdb")

RAW_DIR     = ROOT / "data" / "raw"
PDF_STORE   = ROOT / "data" / "pdf_store"
PDF_STORE.mkdir(parents=True, exist_ok=True)

# ─── Domain metadata catalog ──────────────────────────────────────────────────
# Map folder_name -> default metadata cho cac file khong co metadata rieng
DOMAIN_CATALOG: dict[str, dict] = {
    "giao_thong": {
        "law_type": "nghi_dinh",
        "domain": "giao_thong",
    },
    "dat_dai": {
        "law_type": "luat",
        "domain": "dat_dai",
    },
    "lao_dong": {
        "law_type": "luat",
        "domain": "lao_dong",
    },
    "dan_su": {
        "law_type": "luat",
        "domain": "dan_su",
    },
    "hinh_su": {
        "law_type": "luat",
        "domain": "hinh_su",
    },
    "hon_nhan": {
        "law_type": "luat",
        "domain": "dan_su",   # hon_nhan -> dan_su (khong co domain rieng)
    },
}

# File-level metadata override (neu file co ten cu the)
FILE_METADATA: dict[str, dict] = {
    # Giao thong
    "nd_100_2019.pdf": {
        "law_name": "Nghị định 100/2019/NĐ-CP về xử phạt VPHC giao thông đường bộ",
        "document_code": "100/2019/NĐ-CP",
        "effective_date": "2020-01-01",
    },
    "nd_123_2021.pdf": {
        "law_name": "Nghị định 123/2021/NĐ-CP sửa đổi Nghị định 100/2019",
        "document_code": "123/2021/NĐ-CP",
        "effective_date": "2022-01-01",
    },
    "luat_gtdb_2008.pdf": {
        "law_name": "Luật Giao thông đường bộ 2008",
        "document_code": "23/2008/QH12",
        "effective_date": "2009-07-01",
    },
    # Dat dai
    "luat_dat_dai_2024_phan1.pdf": {
        "law_name": "Luật Đất đai 2024 (Phần 1 - Chương I-VI)",
        "document_code": "31/2024/QH15-P1",
        "effective_date": "2024-08-01",
    },
    "luat_dat_dai_2024_phan2.pdf": {
        "law_name": "Luật Đất đai 2024 (Phần 2 - Chương VII-XII)",
        "document_code": "31/2024/QH15-P2",
        "effective_date": "2024-08-01",
    },
    "luat_dat_dai_2024_phan3.pdf": {
        "law_name": "Luật Đất đai 2024 (Phần 3 - Chương XIII-XVI)",
        "document_code": "31/2024/QH15-P3",
        "effective_date": "2024-08-01",
    },
    # Lao dong
    "bo_luat_lao_dong_2019.pdf": {
        "law_name": "Bộ luật Lao động 2019",
        "document_code": "45/2019/QH14",
        "effective_date": "2021-01-01",
    },
    # Dan su
    "bo_luat_dan_su_2015.pdf": {
        "law_name": "Bộ luật Dân sự 2015",
        "document_code": "91/2015/QH13",
        "effective_date": "2017-01-01",
    },
    # Hon nhan
    "luat_hon_nhan_2014.pdf": {
        "law_name": "Luật Hôn nhân và Gia đình 2014",
        "document_code": "52/2014/QH13",
        "effective_date": "2015-01-01",
    },
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_already_ingested(pg_conn_str: str) -> set[str]:
    """Lay danh sach file_path da ingest de skip."""
    try:
        conn = psycopg2.connect(pg_conn_str)
        cur = conn.cursor()
        cur.execute("SELECT file_path FROM legal_documents WHERE file_path IS NOT NULL")
        rows = {os.path.basename(r[0]) for r in cur.fetchall()}
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[WARN] Can not read existing docs: {e}")
        return set()


def _build_file_list(target_domain: str | None) -> list[tuple[Path, str]]:
    """
    Returns list of (pdf_path, domain_code) to ingest.
    """
    result = []
    for domain_dir in sorted(RAW_DIR.iterdir()):
        if not domain_dir.is_dir():
            continue
        domain = domain_dir.name
        if target_domain and domain != target_domain:
            continue
        if domain not in DOMAIN_CATALOG:
            print(f"[SKIP] Unknown domain folder: {domain}/")
            continue
        for f in sorted(domain_dir.glob("*.pdf")):
            result.append((f, domain))
    return result


# ─── Core ingest (reuse logic tu ingest.py) ───────────────────────────────────

def _ensure_collection(qdrant_client: QdrantClient):
    existing = [c.name for c in qdrant_client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
        print(f"[Qdrant] Created collection '{COLLECTION_NAME}'")


def _ingest_one(pdf_path: Path, domain: str, qdrant_client: QdrantClient, embedder):
    """Ingest mot file PDF vao Qdrant + Postgres."""
    from ingestion.ingest import (
        ingest_document,
        extract_text_from_pdf_with_pages,
        smart_chunk_with_pages,
    )
    from qdrant_client.models import PointStruct

    fname = pdf_path.name
    domain_meta = DOMAIN_CATALOG.get(domain, {})
    file_meta   = FILE_METADATA.get(fname, {})

    # Build document metadata
    doc_meta = {
        "document_id":   str(uuid.uuid4()),
        "law_name":      file_meta.get("law_name", fname.replace("_", " ").replace(".pdf", "").title()),
        "document_code": file_meta.get("document_code", fname.replace(".pdf", "")),
        "law_type":      file_meta.get("law_type") or domain_meta.get("law_type", "luat"),
        "effective_date": file_meta.get("effective_date", "2024-01-01"),
        "expiry_date":   file_meta.get("expiry_date"),
        "domain":        domain_meta.get("domain", domain),
    }

    # Copy PDF -> pdf_store/ (cho pdf viewer)
    dest_pdf = PDF_STORE / fname
    if not dest_pdf.exists():
        shutil.copy2(pdf_path, dest_pdf)
        print(f"  [PDF] Copied to pdf_store/{fname}")

    # Extract text
    print(f"  [1/4] Extracting text from {fname}...")
    pages_dict = extract_text_from_pdf_with_pages(str(pdf_path))

    # Chunk
    print(f"  [2/4] Chunking...")
    chunks = smart_chunk_with_pages(pages_dict, doc_meta)
    print(f"         → {len(chunks)} chunks")

    if not chunks:
        print(f"  [SKIP] No chunks extracted from {fname}")
        return 0

    # Embed
    print(f"  [3/4] Embedding {len(chunks)} chunks...")
    contents = [c["content"] for c in chunks]
    vectors  = embedder.encode(contents, batch_size=32, show_progress_bar=True)

    # Save to Qdrant (with domain in payload)
    print("  [4a/4] Saving to Qdrant...")
    _ensure_collection(qdrant_client)
    source_file = fname
    points = []
    for chunk, vec in zip(chunks, vectors):
        points.append(PointStruct(
            id=chunk["chunk_id"],
            vector=vec.tolist(),
            payload={
                "content":       chunk["content"],
                "article":       chunk.get("article"),
                "article_title": chunk.get("article_title"),
                "clause":        chunk.get("clause"),
                "law_name":      chunk.get("law_name"),
                "document_code": chunk.get("document_code"),
                "law_type":      chunk.get("law_type"),
                "effective_date": chunk.get("effective_date"),
                "expiry_date":   chunk.get("expiry_date"),
                "page_number":   chunk.get("page_number"),
                "source_file":   source_file,
                "document_id":   chunk.get("document_id"),
                "domain":        doc_meta["domain"],   # KEY FIELD for filtering
            },
        ))
    for i in range(0, len(points), 100):
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points[i:i+100])

    # Save to Postgres (with domain)
    print("  [4b/4] Saving to PostgreSQL...")
    conn = psycopg2.connect(PG_CONN)
    cur  = conn.cursor()
    cur.execute(
        """
        INSERT INTO legal_documents
            (id, law_name, document_code, law_type, effective_date, expiry_date,
             file_path, total_chunks, domain)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            law_name = EXCLUDED.law_name,
            document_code = EXCLUDED.document_code,
            law_type = EXCLUDED.law_type,
            effective_date = EXCLUDED.effective_date,
            file_path = EXCLUDED.file_path,
            total_chunks = EXCLUDED.total_chunks,
            domain = EXCLUDED.domain
        """,
        (
            doc_meta["document_id"],
            doc_meta["law_name"],
            doc_meta["document_code"],
            doc_meta.get("law_type"),
            doc_meta["effective_date"],
            doc_meta.get("expiry_date"),
            str(dest_pdf),
            len(chunks),
            doc_meta["domain"],
        ),
    )
    for idx, chunk in enumerate(chunks):
        cur.execute(
            """
            INSERT INTO document_chunks
                (id, document_id, qdrant_id, article, clause, content, page_number, chunk_index)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                chunk["chunk_id"],
                doc_meta["document_id"],
                chunk["chunk_id"],
                chunk.get("article"),
                chunk.get("clause"),
                chunk["content"],
                chunk.get("page_number"),
                idx,
            ),
        )
    conn.commit()
    cur.close()
    conn.close()

    print(f"  ✓ Done: {len(chunks)} chunks ingested [{doc_meta['domain']}]")
    return len(chunks)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except OSError:
            pass

    parser = argparse.ArgumentParser(description="Batch ingest legal PDFs by domain")
    parser.add_argument("--domain", default=None, help="Ingest only this domain folder")
    parser.add_argument("--force",  action="store_true", help="Re-ingest even if already in DB")
    parser.add_argument("--dry-run", action="store_true", help="List files only, no ingest")
    args = parser.parse_args()

    files = _build_file_list(args.domain)
    if not files:
        print(f"No files found in data/raw/{args.domain or '*'}/")
        return

    print(f"\n{'='*60}")
    print(f"  BATCH INGEST — {len(files)} file(s)")
    print(f"  Domain filter: {args.domain or 'ALL'}")
    print(f"  Force re-ingest: {args.force}")
    print(f"{'='*60}\n")

    if args.dry_run:
        for path, domain in files:
            print(f"  [{domain}] {path.name}")
        return

    # Load embedder once
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    qdrant_client = QdrantClient(QDRANT_URL, timeout=120)
    _ensure_collection(qdrant_client)

    # Check already ingested
    already_done = set() if args.force else _get_already_ingested(PG_CONN)
    if already_done:
        print(f"[DB] {len(already_done)} file(s) already ingested (use --force to re-ingest)")

    total_chunks = 0
    skipped = 0

    for i, (pdf_path, domain) in enumerate(files, 1):
        fname = pdf_path.name
        print(f"\n[{i}/{len(files)}] {fname}  ({domain})")
        print(f"{'─'*52}")

        if fname in already_done:
            print(f"  [SKIP] Already ingested (use --force to override)")
            skipped += 1
            continue

        try:
            n = _ingest_one(pdf_path, domain, qdrant_client, embedder)
            total_chunks += n
        except Exception as e:
            print(f"  [ERROR] Failed to ingest {fname}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  Files processed : {len(files) - skipped}")
    print(f"  Files skipped   : {skipped}")
    print(f"  Total chunks    : {total_chunks}")
    print(f"{'='*60}\n")

    # Summary by domain
    print("Domain summary in DB:")
    try:
        conn = psycopg2.connect(PG_CONN)
        cur  = conn.cursor()
        cur.execute("""
            SELECT domain, COUNT(*) as docs, SUM(total_chunks) as chunks
            FROM legal_documents
            GROUP BY domain ORDER BY docs DESC
        """)
        for row in cur.fetchall():
            print(f"  {row[0]:<15} {row[1]} docs  {row[2]} chunks")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"  Could not fetch summary: {e}")


if __name__ == "__main__":
    main()
