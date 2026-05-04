"""
ingestion/file_watcher.py
=========================
Theo dõi thư mục data/raw/<domain>/ — tự động re-ingest khi file thay đổi.

Luồng hoạt động:
  1. watchdog Observer theo dõi recursive data/raw/
  2. Khi có file .pdf mới / bị modify:
     - Detect domain từ tên thư mục cha
     - Debounce 3 giây (tránh trigger nhiều lần khi copy file lớn)
     - Xóa chunks cũ trong Qdrant + PostgreSQL (nếu có)
     - Re-ingest file vào Qdrant + PostgreSQL trong background thread

Tích hợp vào FastAPI startup:
    from ingestion.file_watcher import start_watcher
    threading.Thread(target=start_watcher, args=(watch_dir,), daemon=True).start()

Chạy độc lập (debug):
    cd backend-python
    .venv\\Scripts\\python.exe ingestion/file_watcher.py
"""
from __future__ import annotations

import os
import sys
import time
import threading
import uuid
from pathlib import Path

# Force UTF-8 stdout — chạy trên Windows terminal (cp1252) sẽ crash khi print emoji/tiếng Việt
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import psycopg2
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import FilterSelector, Filter, FieldCondition, MatchValue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Docker: fastembed (ONNX, no torch); Local: sentence_transformers fallback
try:
    from fastembed import TextEmbedding
    _USE_FASTEMBED = True
except ImportError:
    from sentence_transformers import SentenceTransformer
    _USE_FASTEMBED = False

# Thêm root vào sys.path để import ingestion modules
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT.parent / ".env", override=True)

# ─── Config ───────────────────────────────────────────────────────────────────
QDRANT_URL      = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "legal_chunks")
EMBEDDING_MODEL          = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
FASTEMBED_EMBEDDING_MODEL = os.getenv("FASTEMBED_EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
PG_CONN         = os.getenv("POSTGRES_URL", "postgresql://raguser:ragpass@localhost:5432/ragdb")

# Các domain được hỗ trợ — phải khớp với DOMAIN_CATALOG trong batch_ingest.py
SUPPORTED_DOMAINS = {"giao_thong", "dat_dai", "lao_dong", "dan_su", "hinh_su", "hon_nhan"}

# Debounce delay (giây) — tránh trigger liên tục khi OS ghi file theo chunk
_DEBOUNCE_SECONDS = 3.0


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _detect_domain(filepath: str) -> str | None:
    """
    Detect domain từ tên thư mục cha của file.
    Ví dụ: data/raw/giao_thong/nd_100_2019.pdf → "giao_thong"
    """
    parts = Path(filepath).parts
    for part in reversed(parts[:-1]):  # bỏ tên file, duyệt ngược
        if part in SUPPORTED_DOMAINS:
            return part
    return None


def _delete_existing_chunks(file_basename: str, pg_conn_str: str, qdrant_client: QdrantClient):
    """
    Xóa toàn bộ chunks cũ của file trên cả Qdrant + PostgreSQL.
    Dùng file_path (basename) để định danh — phải match với cách batch_ingest.py lưu.
    """
    try:
        conn = psycopg2.connect(pg_conn_str)
        cur = conn.cursor()

        # Tìm tất cả document_id có basename của file_path khớp
        cur.execute(
            "SELECT id FROM legal_documents WHERE file_path LIKE %s",
            (f"%{file_basename}",),
        )
        doc_ids = [str(r[0]) for r in cur.fetchall()]

        if not doc_ids:
            print(f"[Watcher] Không tìm thấy bản ghi cũ cho: {file_basename}")
            cur.close()
            conn.close()
            return

        for doc_id in doc_ids:
            # Lấy qdrant_ids để xóa khỏi vector store
            cur.execute(
                "SELECT qdrant_id FROM document_chunks WHERE document_id = %s",
                (doc_id,),
            )
            qdrant_ids = [str(r[0]) for r in cur.fetchall()]

            if qdrant_ids:
                try:
                    qdrant_client.delete(
                        collection_name=COLLECTION_NAME,
                        points_selector=FilterSelector(
                            filter=Filter(
                                must=[
                                    FieldCondition(
                                        key="document_id",
                                        match=MatchValue(value=doc_id),
                                    )
                                ]
                            )
                        ),
                    )
                    print(f"[Watcher] Xóa {len(qdrant_ids)} vectors khỏi Qdrant (doc={doc_id})")
                except Exception as e:
                    print(f"[Watcher] WARN: Lỗi xóa Qdrant: {e}")

            # Xóa khỏi PostgreSQL
            cur.execute("DELETE FROM document_chunks WHERE document_id = %s", (doc_id,))
            cur.execute("DELETE FROM legal_documents WHERE id = %s", (doc_id,))
            print(f"[Watcher] Xóa document cũ khỏi PostgreSQL: {doc_id}")

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Watcher] ERROR trong _delete_existing_chunks: {e}")


def _build_doc_meta(pdf_path: Path, domain: str) -> dict:
    """
    Xây dựng document metadata — tìm trong FILE_METADATA của batch_ingest.py,
    fallback về tên file nếu không tìm thấy.
    """
    from ingestion.batch_ingest import FILE_METADATA, DOMAIN_CATALOG

    fname = pdf_path.name
    domain_meta = DOMAIN_CATALOG.get(domain, {})
    file_meta   = FILE_METADATA.get(fname, {})

    return {
        "document_id":   str(uuid.uuid4()),
        "law_name":      file_meta.get("law_name", fname.replace("_", " ").replace(".pdf", "").title()),
        "document_code": file_meta.get("document_code", fname.replace(".pdf", "")),
        "law_type":      file_meta.get("law_type") or domain_meta.get("law_type", "luat"),
        "effective_date": file_meta.get("effective_date", "2024-01-01"),
        "expiry_date":   file_meta.get("expiry_date"),
        "domain":        domain_meta.get("domain", domain),
    }


def _do_ingest(pdf_path: Path, domain: str):
    """
    Chạy trong background thread:
      1. Xóa chunks cũ (nếu có)
      2. Extract text + chunk
      3. Embed + lưu Qdrant + PostgreSQL
    """
    from ingestion.ingest import extract_text_from_pdf_with_pages, smart_chunk_with_pages

    fname = pdf_path.name
    print(f"\n[Watcher] {'='*50}")
    print(f"[Watcher] Re-ingesting: {pdf_path}")

    # Đợi file ghi xong (tránh race condition khi copy file lớn)
    time.sleep(1.0)
    if not pdf_path.exists():
        print(f"[Watcher] File không tồn tại sau debounce: {pdf_path}")
        return

    qdrant_client = QdrantClient(QDRANT_URL, timeout=120)
    if _USE_FASTEMBED:
        embedder = TextEmbedding(model_name=FASTEMBED_EMBEDDING_MODEL)
    else:
        embedder = SentenceTransformer(EMBEDDING_MODEL)

    # Step 1: Xóa chunks cũ
    _delete_existing_chunks(fname, PG_CONN, qdrant_client)

    # Step 2: Build metadata
    doc_meta = _build_doc_meta(pdf_path, domain)

    # Step 3: Ingest (reuse logic từ batch_ingest._ingest_one)
    try:
        from ingestion.batch_ingest import _ingest_one, PDF_STORE
        import shutil

        # Copy sang pdf_store nếu chưa có
        dest_pdf = PDF_STORE / fname
        if not dest_pdf.exists() or dest_pdf.stat().st_mtime < pdf_path.stat().st_mtime:
            shutil.copy2(pdf_path, dest_pdf)

        # Dùng lại _ingest_one
        n = _ingest_one(pdf_path, domain, qdrant_client, embedder)
        print(f"[Watcher] ✅ Re-ingest xong: {fname} — {n} chunks")
    except Exception as e:
        print(f"[Watcher] ❌ Lỗi re-ingest {fname}: {e}")
        import traceback
        traceback.print_exc()


# ─── Watchdog Event Handler ───────────────────────────────────────────────────

class LegalDocumentHandler(FileSystemEventHandler):
    """
    Xử lý sự kiện file thay đổi trong data/raw/.
    Chỉ xử lý .pdf (+ .docx nếu cần sau này).
    Debounce 3 giây để tránh trigger liên tục.
    """

    def __init__(self):
        super().__init__()
        self._debounce: dict[str, float] = {}
        self._lock = threading.Lock()

    def on_created(self, event):
        if not event.is_directory and self._is_legal_file(event.src_path):
            print(f"[Watcher] 📄 File mới: {event.src_path}")
            self._handle(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._is_legal_file(event.src_path):
            print(f"[Watcher] 🔄 File thay đổi: {event.src_path}")
            self._handle(event.src_path)

    def on_moved(self, event):
        # Khi file được rename/move vào thư mục raw/
        if not event.is_directory and self._is_legal_file(event.dest_path):
            print(f"[Watcher] 📦 File move/rename → {event.dest_path}")
            self._handle(event.dest_path)

    @staticmethod
    def _is_legal_file(filepath: str) -> bool:
        return filepath.lower().endswith((".pdf",))  # mở rộng thêm .docx nếu cần

    def _handle(self, filepath: str):
        # Debounce: bỏ qua nếu đã xử lý gần đây
        now = time.time()
        with self._lock:
            if now - self._debounce.get(filepath, 0) < _DEBOUNCE_SECONDS:
                return
            self._debounce[filepath] = now

        domain = _detect_domain(filepath)
        if not domain:
            print(f"[Watcher] ⚠️ Không detect được domain từ path: {filepath}")
            print(f"           Đặt file vào đúng thư mục: data/raw/<domain>/file.pdf")
            return

        pdf_path = Path(filepath)
        # Chạy trong thread riêng — không block event loop của watchdog
        thread = threading.Thread(
            target=_do_ingest,
            args=(pdf_path, domain),
            daemon=True,
            name=f"watcher-ingest-{pdf_path.name}",
        )
        thread.start()


# ─── Public API ───────────────────────────────────────────────────────────────

def start_watcher(watch_dir: str | None = None):
    """
    Khởi động watchdog observer và block (dùng trong daemon thread).

    Args:
        watch_dir: Đường dẫn tới thư mục cần theo dõi.
                   Mặc định: <backend-python>/data/raw/
    """
    if watch_dir is None:
        watch_dir = str(ROOT / "data" / "raw")

    Path(watch_dir).mkdir(parents=True, exist_ok=True)

    handler = LegalDocumentHandler()
    observer = Observer()
    observer.schedule(handler, path=watch_dir, recursive=True)
    observer.start()
    print(f"[Watcher] 👀 Theo dõi: {watch_dir}")
    print(f"[Watcher]    Thêm/sửa file .pdf → tự động re-ingest")

    try:
        while True:
            time.sleep(1)
            if not observer.is_alive():
                print("[Watcher] Observer dừng bất thường, khởi động lại...")
                observer.start()
    except (KeyboardInterrupt, SystemExit):
        observer.stop()
    observer.join()
    print("[Watcher] Đã dừng.")


# ─── Standalone (debug) ───────────────────────────────────────────────────────

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except OSError:
            pass
    start_watcher()
