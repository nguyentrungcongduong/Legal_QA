import os
import sys

import psycopg2
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv("../.env", override=True)


def test_qdrant() -> None:
    qdrant_url = os.getenv("QDRANT_URL")
    if not qdrant_url:
        raise ValueError("Missing QDRANT_URL in .env")

    qdrant = QdrantClient(qdrant_url)
    collections = qdrant.get_collections()
    print("Qdrant collections:", collections)


def test_postgres() -> None:
    postgres_url = os.getenv("POSTGRES_URL")
    if not postgres_url:
        raise ValueError("Missing POSTGRES_URL in .env")

    conn = psycopg2.connect(postgres_url)
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    print("PostgreSQL tables:", cur.fetchall())
    cur.close()
    conn.close()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except OSError:
            pass
    test_qdrant()
    test_postgres()
    print("Tất cả kết nối OK!")
