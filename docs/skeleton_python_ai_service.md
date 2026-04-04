Bước 1: Ingestion Script
python# ingestion/ingest.py
import re
import uuid
import fitz  # PyMuPDF
import psycopg2
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from sentence_transformers import SentenceTransformer

# ============================================================
# CONFIG
# ============================================================
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "legal_chunks"
EMBEDDING_MODEL = "BAAI/bge-m3"
PG_CONN = "postgresql://user:pass@localhost:5432/ragdb"

qdrant = QdrantClient(QDRANT_URL)
embedder = SentenceTransformer(EMBEDDING_MODEL)

# ============================================================
# STEP 1: ĐỌC PDF + CLEAN
# ============================================================
def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        text = page.get_text("text")
        text = clean_text(text)
        pages.append(text)
    return "\n".join(pages)

def clean_text(text: str) -> str:
    # Xóa watermark, header/footer lặp lại
    text = re.sub(r'Trang \d+ / \d+', '', text)
    text = re.sub(r'©.*?\n', '', text)
    # Xóa dòng trắng thừa
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Xóa khoảng trắng thừa
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

# ============================================================
# STEP 2: SMART CHUNKING — tách theo Điều/Khoản
# ============================================================
def smart_chunk(text: str, document_metadata: dict) -> list[dict]:
    chunks = []

    # Regex nhận diện bắt đầu Điều
    dieu_pattern = re.compile(
        r'(Điều\s+(\d+)\s*[.\:]\s*[^\n]+(?:\n(?!Điều\s+\d+).*)*)',
        re.MULTILINE
    )

    for match in dieu_pattern.finditer(text):
        dieu_text = match.group(1).strip()
        dieu_number = match.group(2)
        dieu_title_line = dieu_text.split('\n')[0]

        # Tách tiếp theo Khoản bên trong Điều
        khoan_pattern = re.compile(
            r'(\d+\.\s.+?)(?=\n\d+\.\s|\Z)',
            re.DOTALL
        )
        khoan_matches = list(khoan_pattern.finditer(dieu_text))

        if khoan_matches:
            for km in khoan_matches:
                khoan_text = km.group(1).strip()
                khoan_number = khoan_text.split('.')[0]

                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "content": khoan_text,
                    "article": f"Điều {dieu_number}",
                    "article_title": dieu_title_line,
                    "clause": f"Khoản {khoan_number}",
                    "full_article_text": dieu_text,  # context đầy đủ
                    **document_metadata
                })
        else:
            # Điều không có khoản → chunk cả Điều
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "content": dieu_text,
                "article": f"Điều {dieu_number}",
                "article_title": dieu_title_line,
                "clause": None,
                "full_article_text": dieu_text,
                **document_metadata
            })

    return chunks

# ============================================================
# STEP 3: EMBED + LƯU VÀO QDRANT VÀ POSTGRES
# ============================================================
def ingest_document(pdf_path: str, document_metadata: dict):
    print(f"[1/4] Đọc PDF: {pdf_path}")
    text = extract_text_from_pdf(pdf_path)

    print(f"[2/4] Smart chunking...")
    chunks = smart_chunk(text, document_metadata)
    print(f"      → {len(chunks)} chunks")

    print(f"[3/4] Embedding {len(chunks)} chunks...")
    contents = [c["content"] for c in chunks]
    vectors = embedder.encode(contents, batch_size=32, show_progress_bar=True)

    print(f"[4/4] Lưu vào Qdrant + PostgreSQL...")
    _save_to_qdrant(chunks, vectors)
    _save_to_postgres(chunks, document_metadata)

    print(f"Done! Ingested {len(chunks)} chunks.")

def _save_to_qdrant(chunks: list, vectors):
    # Tạo collection nếu chưa có
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )

    points = []
    for chunk, vector in zip(chunks, vectors):
        points.append(PointStruct(
            id=chunk["chunk_id"],
            vector=vector.tolist(),
            payload={
                "content": chunk["content"],
                "article": chunk["article"],
                "article_title": chunk["article_title"],
                "clause": chunk["clause"],
                "law_name": chunk["law_name"],
                "document_code": chunk["document_code"],
                "law_type": chunk["law_type"],
                "effective_date": chunk["effective_date"],
                "expiry_date": chunk.get("expiry_date"),
                "page_number": chunk.get("page_number"),
                "document_id": chunk["document_id"],
            }
        ))

    # Upsert theo batch 100
    for i in range(0, len(points), 100):
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points[i:i+100]
        )

def _save_to_postgres(chunks: list, doc_meta: dict):
    conn = psycopg2.connect(PG_CONN)
    cur = conn.cursor()
    for chunk in chunks:
        cur.execute("""
            INSERT INTO document_chunks
                (id, document_id, qdrant_id, article, clause, content, chunk_index)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            chunk["chunk_id"],
            doc_meta["document_id"],
            chunk["chunk_id"],
            chunk["article"],
            chunk["clause"],
            chunk["content"],
            chunks.index(chunk)
        ))
    conn.commit()
    cur.close()
    conn.close()

# ============================================================
# CHẠY
# ============================================================
if __name__ == "__main__":
    ingest_document(
        pdf_path="data/nd_100_2019.pdf",
        document_metadata={
            "document_id": str(uuid.uuid4()),
            "law_name": "Nghị định 100/2019/NĐ-CP",
            "document_code": "100/2019/ND-CP",
            "law_type": "nghi_dinh",
            "effective_date": "2020-01-01",
            "expiry_date": None,
        }
    )

Bước 2: Hybrid Retriever
python# retriever/hybrid_retriever.py
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, Range
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import psycopg2
from datetime import date

class HybridRetriever:

    def __init__(self):
        self.qdrant = QdrantClient(QDRANT_URL)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        self.pg_conn = PG_CONN

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        # Chạy song song Dense + Sparse
        dense_results = self._dense_search(query, top_k)
        sparse_results = self._sparse_search(query, top_k)

        # Merge bằng Reciprocal Rank Fusion
        merged = self._reciprocal_rank_fusion(
            dense_results, sparse_results, top_k
        )
        return merged

    # ---- Dense Search (Qdrant vector) ----
    def _dense_search(self, query: str, top_k: int) -> list[dict]:
        query_vector = self.embedder.encode(query).tolist()

        # Filter chỉ lấy văn bản còn hiệu lực
        results = self.qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="effective_date",
                        range=Range(lte=str(date.today()))
                    )
                ],
                should=[
                    FieldCondition(key="expiry_date", is_null=True)
                ]
            ),
            limit=top_k,
            with_payload=True
        )

        return [
            {**r.payload, "dense_score": r.score, "id": r.id}
            for r in results
        ]

    # ---- Sparse Search (BM25) ----
    def _sparse_search(self, query: str, top_k: int) -> list[dict]:
        # Lấy tất cả chunks từ Postgres để build BM25 index
        # Trong thực tế nên cache index này
        conn = psycopg2.connect(self.pg_conn)
        cur = conn.cursor()
        cur.execute("SELECT id, content FROM document_chunks")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        ids = [r[0] for r in rows]
        corpus = [r[1].split() for r in rows]

        bm25 = BM25Okapi(corpus)
        query_tokens = query.split()
        scores = bm25.get_scores(query_tokens)

        # Lấy top_k index cao nhất
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        return [
            {"id": ids[i], "sparse_score": scores[i]}
            for i in top_indices
        ]

    # ---- Reciprocal Rank Fusion ----
    def _reciprocal_rank_fusion(
        self,
        dense: list,
        sparse: list,
        top_k: int,
        k: int = 60
    ) -> list[dict]:

        scores = {}

        for rank, item in enumerate(dense):
            doc_id = str(item["id"])
            scores.setdefault(doc_id, {"item": item, "rrf_score": 0})
            scores[doc_id]["rrf_score"] += 1 / (k + rank + 1)

        for rank, item in enumerate(sparse):
            doc_id = str(item["id"])
            scores.setdefault(doc_id, {"item": item, "rrf_score": 0})
            scores[doc_id]["rrf_score"] += 1 / (k + rank + 1)

        ranked = sorted(
            scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )[:top_k]

        return [r["item"] for r in ranked]

Bước 3: Generator với Prompt chuẩn
python# generator/generator.py
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
Bạn là chuyên gia pháp luật giao thông đường bộ Việt Nam với 20 năm kinh nghiệm tư vấn.

NGUYÊN TẮC BẮT BUỘC:
1. CHỈ sử dụng thông tin từ các đoạn văn bản pháp luật được cung cấp
2. Mỗi thông tin PHẢI kèm trích dẫn [số] tương ứng với nguồn
3. Nếu không tìm thấy thông tin: trả lời "Tôi không tìm thấy quy định cụ thể về vấn đề này"
4. Nếu thông tin không đủ để khẳng định chắc chắn, nêu rõ điều kiện cần thiết
   hoặc khuyên tham khảo thêm cơ quan chức năng, tuyệt đối không đưa ra kết luận giả định
5. TUYỆT ĐỐI không thêm thông tin ngoài văn bản được cung cấp
6. Nếu có mâu thuẫn giữa các văn bản, ưu tiên văn bản có hiệu lực mới hơn

ĐỊNH DẠNG TRẢ LỜI:
1. Căn cứ pháp lý: [liệt kê điều luật áp dụng]
2. Nội dung tư vấn: [giải thích có trích dẫn [1][2]...]
3. Kết luận: [tóm tắt ngắn gọn]
"""

class Generator:

    def generate(
        self,
        query: str,
        chunks: list[dict],
        conflicts: list[dict] = None
    ) -> dict:

        # Build context từ chunks
        context = self._build_context(chunks)

        # Thêm cảnh báo conflict nếu có
        conflict_notice = ""
        if conflicts:
            conflict_notice = "\n⚠️ LƯU Ý XUNG ĐỘT VĂN BẢN:\n"
            for c in conflicts:
                conflict_notice += (
                    f"- {c['description']}. "
                    f"Áp dụng: {c['applied_source']}\n"
                )

        user_prompt = f"""
VĂN BẢN PHÁP LUẬT LIÊN QUAN:
{context}
{conflict_notice}
---
CÂU HỎI: {query}

Trả lời theo đúng định dạng yêu cầu, có trích dẫn [số].
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0  # deterministic cho legal
        )

        answer = response.choices[0].message.content

        return {
            "answer": answer,
            "citations": self._build_citations(chunks),
            "has_conflict": bool(conflicts),
            "conflicts": conflicts or []
        }

    def _build_context(self, chunks: list[dict]) -> str:
        lines = []
        for i, chunk in enumerate(chunks, 1):
            lines.append(f"""
[{i}] {chunk['law_name']} — {chunk['article']}, {chunk.get('clause', '')}
Hiệu lực từ: {chunk['effective_date']}
Nội dung: {chunk['content']}
""")
        return "\n".join(lines)

    def _build_citations(self, chunks: list[dict]) -> list[dict]:
        return [
            {
                "index": i,
                "law_name": c["law_name"],
                "article": c["article"],
                "clause": c.get("clause"),
                "content": c["content"],
                "effective_date": c["effective_date"],
                "relevance_score": c.get("dense_score", 0)
            }
            for i, c in enumerate(chunks, 1)
        ]

Bước 4: Ghép lại thành FastAPI endpoint
python# main.py
from fastapi import FastAPI
from retriever.hybrid_retriever import HybridRetriever
from reranker.reranker import Reranker
from generator.generator import Generator
from conflict_detector.detector import ConflictDetector
from guard.query_guard import QueryGuard

app = FastAPI()

retriever = HybridRetriever()
reranker = Reranker()
generator = Generator()
conflict_detector = ConflictDetector()
query_guard = QueryGuard()

@app.post("/ai/query")
async def query(request: dict):
    q = request["query"]

    # 1. Guard
    if query_guard.is_out_of_domain(q):
        return {
            "answer": "Hệ thống chỉ hỗ trợ tra cứu luật giao thông đường bộ.",
            "citations": [],
            "out_of_domain": True
        }

    # 2. Retrieve
    chunks = retriever.search(q, top_k=20)

    # 3. Rerank
    reranked = reranker.rerank(q, chunks, top_k=5)

    # 4. Conflict detection
    result = conflict_detector.detect_and_resolve(reranked)

    # 5. Generate
    response = generator.generate(
        query=q,
        chunks=result["resolved_chunks"],
        conflicts=result["conflicts"]
    )

    return response