import psycopg2, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')

conn = psycopg2.connect(os.getenv('POSTGRES_URL'))
cur = conn.cursor()

# Schema
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='legal_documents' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print('Columns in legal_documents:', cols)
print()

# Total chunks in Qdrant proxy (PostgreSQL side)
cur.execute("SELECT COUNT(*) FROM document_chunks")
total_chunks = cur.fetchone()[0]

# Files ingested
cur.execute("SELECT file_path, domain, created_at FROM legal_documents ORDER BY created_at")
rows = cur.fetchall()

print(f"Total files ingested : {len(rows)}")
print(f"Total chunks in DB   : {total_chunks}")
print()
for r in rows:
    fname = r[0].replace('\\', '/').split('/')[-1]
    print(f"  [{r[1]:12s}] {fname}")
