import os
import sys
import psycopg2
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv(override=True)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except OSError:
        pass

PG_CONN = os.getenv("POSTGRES_URL", "postgresql://raguser:ragpass@localhost:5432/ragdb")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "legal_chunks")

def wipe_data():
    print("🧹 Bắt đầu dọn dẹp RAG Database...")
    
    # 1. Xóa Postgres
    try:
        conn = psycopg2.connect(PG_CONN)
        cur = conn.cursor()
        cur.execute("DELETE FROM document_chunks;")
        cur.execute("DELETE FROM legal_documents;")
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Đã xóa toàn bộ dữ liệu trong PostgreSQL (bảng legal_documents và document_chunks).")
    except Exception as e:
        print(f"❌ Lỗi xóa Postgres: {e}")

    # 2. Xóa Qdrant
    try:
        # Thay thế localhost bằng 127.0.0.1 để tránh lỗi phân giải IPv6 trên Windows
        q_url = QDRANT_URL.replace("localhost", "127.0.0.1")
        client = QdrantClient(q_url, timeout=120.0)
        existing = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME in existing:
            client.delete_collection(collection_name=COLLECTION_NAME)
            print(f"✅ Đã xóa collection '{COLLECTION_NAME}' trong Qdrant.")
        else:
            print(f"✅ Collection '{COLLECTION_NAME}' trong Qdrant đã trống sẵn.")
    except Exception as e:
        print(f"❌ Lỗi xóa Qdrant: {e}")

    print("🎉 Dọn dẹp hoàn tất! Giờ bạn có thể chạy `ingest.py` để nạp dữ liệu sạch 100% không bị trùng lặp.")

if __name__ == "__main__":
    wipe_data()
