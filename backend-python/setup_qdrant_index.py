"""
setup_qdrant_index.py
Chạy 1 lần để tạo payload index cho field 'domain' trong Qdrant.
Sau khi có index, filtered search sẽ là O(log n) thay vì O(n) full-scan.

Usage:
    python setup_qdrant_index.py
"""
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType

QDRANT_URL       = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME  = os.getenv("COLLECTION_NAME", "legal_chunks")

client = QdrantClient(QDRANT_URL, timeout=60)

print(f"[setup] Qdrant: {QDRANT_URL}  collection: {COLLECTION_NAME}")

# 1. Payload index on 'domain' — enables fast keyword-filtered ANN
print("[setup] Creating payload index on 'domain'...")
client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="domain",
    field_schema=PayloadSchemaType.KEYWORD,
)
print("[setup] 'domain' index: OK")

# 2. Optional: payload index on 'article' field (used by vehicle_boost verify)
print("[setup] Creating payload index on 'article'...")
client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="article",
    field_schema=PayloadSchemaType.KEYWORD,
)
print("[setup] 'article' index: OK")

print("\n[setup] Done. Restart FastAPI to benefit from the new indexes.")
