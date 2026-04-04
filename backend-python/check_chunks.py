import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except OSError:
            pass

    url = os.getenv("POSTGRES_URL")
    if not url:
        raise SystemExit("Thiếu POSTGRES_URL trong .env")

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT article, clause, LEFT(content, 100)
        FROM document_chunks
        LIMIT 10
        """
    )

    for row in cur.fetchall():
        print(f"Article: {row[0]}")
        print(f"Clause:  {row[1]}")
        print(f"Content: {row[2]}")
        print("-" * 50)

    cur.execute(
        """
        SELECT article, COUNT(*) AS chunk_count
        FROM document_chunks
        GROUP BY article
        ORDER BY article
        LIMIT 20
        """
    )

    print("\nSố chunks theo Điều:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} chunks")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
