# Kiến trúc Hệ thống — Legal QA

> Mô tả **đúng theo code thực tế** (không phải bản thiết kế ban đầu)

---

## Tổng quan

```
Vue.js :5173  →  Spring Boot :8081  →  FastAPI :8000  →  Qdrant :6333
                  (Gateway + Auth)      (RAG Core)         PostgreSQL :5432
```

**Hybrid mode:** Docker chạy Qdrant + PostgreSQL, ứng dụng chạy native (không containerize).

---

## Layer 1: Vue.js Frontend (Vite + Vue 3 + Pinia)

**5 màn hình chính:**
- `LandingView` — trang giới thiệu, mô tả pipeline RAG bằng diagram
- `LoginView / RegisterView` — xác thực JWT
- `ChatView` — giao diện chat chính với RAG, citation panel, typewriter effect
- `CompareView` — so sánh RAG vs Vanilla LLM (Groq) trực quan 2 cột
- `EvaluationView` — dashboard đánh giá batch với LLM-as-a-judge
- `AdminView` — upload/ingest tài liệu, quản lý user, xem trạng thái Qdrant

**State management:** Pinia (`authStore`, `historyStore`)
**HTTP client:** Axios với interceptor tự động gắn JWT header

---

## Layer 2: Spring Boot :8081 (Java — Gateway & Orchestration)

Spring Boot **không xử lý AI** — chỉ làm 3 việc:

| Trách nhiệm | Chi tiết |
|-------------|---------|
| **Auth (JWT)** | Tạo/verify JWT token, `JwtAuthFilter` chặn mọi request không có token |
| **Proxy sang FastAPI** | `AiProxyController` forward request xuống `localhost:8000`, kèm JWT header |
| **Lưu history** | Chat messages + sessions lưu vào PostgreSQL |

**Timeout config** (`AiProxyController`):
- `/ai/query`, `/ai/compare` → **2 phút** (model load chậm)
- `/ai/evaluate` → **10 phút** (LLM-as-a-judge chạy nhiều test case)

---

## Layer 3: FastAPI :8000 (Python — RAG Core)

Toàn bộ AI logic nằm ở đây. Pipeline xử lý **tuần tự 5 tầng**:

### Pipeline `/ai/query`

```
Câu hỏi user
    ↓
[1] QueryRewriter (guard/query_rewriter.py)
    - Dùng Groq Llama 3.3 70B
    - Nếu small-talk → trả lời ngay, không chạy RAG
    - Nếu follow-up ("cái đó thì sao?") → rewrite thành câu độc lập
    - Có cache để tránh gọi LLM lặp lại
    ↓
[2] DomainRouter (guard/domain_router.py)
    - Phân loại: giao_thong | dan_su | dat_dai | lao_dong | hinh_su
    - Nếu OOD → từ chối lịch sự
    ↓
[3] HybridRetriever (retriever/hybrid_retriever.py)
    - Dense search: BAAI/bge-m3 (1024 chiều) → Qdrant cosine similarity
    - Sparse search: BM25Okapi → PostgreSQL full-text
    - Merge bằng RRF (Reciprocal Rank Fusion): score = 1/(60+rank_dense) + 1/(60+rank_sparse)
    - Filter theo domain trong Qdrant payload
    - OOD Guard: top chunk score < 0.45 → từ chối
    ↓
[4] ConflictDetector (retriever/conflict_detector.py)
    - Phát hiện chunks mâu thuẫn (cùng Điều/Khoản, nội dung khác)
    - Ưu tiên giữ văn bản có effective_date mới hơn
    ↓
[5] Generator (generator/generator.py)
    - Groq Llama 3.3 70B (hoặc Llama 4 Scout)
    - Prompt template: câu hỏi + chunks + lịch sử chat + domain context
    - Parse [1][2][3] citations từ output
    - Trả JSON: answer + citations + rewritten_query + domain info
```

### Pipeline `/ai/compare`

```
Chạy 2 pipeline SONG SONG:
    ├── RAG pipeline đầy đủ (như trên)
    └── Vanilla LLM: Groq Llama 3.3 70B (chỉ câu hỏi, không có context RAG)
Trả về 2 kết quả để Vue render so sánh 2 cột
```

> ❌ **Không có LLM Router (GPT-4o/Gemini/Claude)** — hệ thống chỉ dùng **Groq API**

### Pipeline `/ai/evaluate`

```
Nhận danh sách test cases (câu hỏi + expected answer)
    ↓
Chạy RAG pipeline cho từng câu hỏi
    ↓
LLM-as-a-Judge: Groq chấm điểm faithfulness, relevancy, hallucination
    ↓
Trả metrics: faithfulness_score, answer_relevancy, hallucination_rate
```

> ❌ **Không dùng RAGAS** — dùng **LLM-as-a-judge tự xây** bằng Groq

---

## Layer 4: Storage

| Kho lưu | Dữ liệu | Mục đích |
|---------|---------|---------|
| **Qdrant :6333** | Vector 1024 chiều + payload (content, article, clause, law_name, domain, page_number) | Dense search (semantic) |
| **PostgreSQL :5432** | users, chat_sessions, chat_messages, legal_documents, document_chunks, message_citations | Metadata, BM25 full-text, history |

### Ingestion Pipeline (`ingestion/ingest.py`)

```
PDF/DOCX
  ↓ PyMuPDF (fitz) / python-docx — đọc từng trang
  ↓ clean_text() — xóa watermark, fix chữ dính
  ↓ smart_chunk_with_pages() — tách theo Điều/Khoản (regex)
  ↓ BAAI/bge-m3 encode — batch_size=4 tránh OOM
  ↓ Qdrant upsert (batch 100 points)
  ↓ PostgreSQL insert (legal_documents + document_chunks)
```

**File watcher** (`ingestion/file_watcher.py`): tự động ingest khi có file mới drop vào thư mục `data/raw/`

---

## Luồng dữ liệu đầy đủ khi user hỏi

```
1. User gõ câu hỏi → Vue gửi POST /api/ai/query (Spring Boot :8081)
2. JwtAuthFilter verify JWT
3. AiProxyController forward → POST /ai/query (FastAPI :8000)
4. FastAPI: QueryRewriter → DomainRouter → HybridRetriever → ConflictDetector → Generator
5. FastAPI trả JSON: { answer, citations, rewritten_query, detected_domain }
6. Spring Boot lưu messages vào PostgreSQL
7. Spring Boot trả response về Vue
8. Vue: typewriter effect + render citation chips + thought trace
```

---

## Deployment (Hybrid Mode)

| Thành phần | Chạy trên |
|-----------|----------|
| Qdrant | Docker (`rag-qdrant`) |
| PostgreSQL | Docker (`rag-postgres`) |
| FastAPI | Native Python (`.venv`) |
| Spring Boot | Native Java (JAR `-Xmx512m`) |
| Vue | Native Node.js (`npm run dev`) |

**Startup:** `.\start.ps1` — tự động dọn container lạ, start theo thứ tự, health check từng service.

---

## Công nghệ thực tế

| Thành phần | Công nghệ |
|-----------|----------|
| Embedding model | `BAAI/bge-m3` (dim=1024, multilingual) |
| LLM cho RAG + Evaluation | `Groq API` — Llama 3.3 70B / Llama 4 Scout |
| Dense search | Qdrant cosine similarity |
| Sparse search | `rank_bm25` (BM25Okapi) |
| Merge strategy | RRF (Reciprocal Rank Fusion) |
| Evaluation method | **LLM-as-a-judge** (tự xây, không phải RAGAS) |
| Auth | JWT (`python-jose` + Spring Security) |
| Frontend state | Pinia stores |