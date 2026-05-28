# 09 · Kiến Trúc Hệ Thống Tổng Quan

> **Tổng hợp:** Toàn bộ stack kỹ thuật và luồng dữ liệu của Legal QA

---

## Stack kỹ thuật

| Tầng | Công nghệ | Cổng | Vai trò |
|------|-----------|------|---------|
| **Frontend** | Vue 3 + Vite + Pinia | `:5173` | Giao diện người dùng |
| **API Gateway** | Spring Boot 3 (Java) | `:8081` | Auth, proxy, history |
| **AI Backend** | FastAPI (Python) | `:8000` | RAG pipeline, AI models |
| **Vector DB** | Qdrant | `:6333` | Lưu trữ embeddings |
| **Relational DB** | PostgreSQL | `:5432` | Users, sessions, metadata |
| **Embedding Model** | BAAI/bge-m3 | — | Vector 1024 chiều |
| **LLM** | Groq (Llama 3.3/4) | — | Sinh câu trả lời |

---

## Sơ đồ kiến trúc

```
User Browser
    │
    │ HTTP (JWT)
    ▼
Vue.js :5173 (Frontend)
    │
    │ REST API (JWT forwarding)
    ▼
Spring Boot :8081 (API Gateway)
    │              │
    │ Auth/History  │ Proxy AI requests
    │              │
    ▼              ▼
PostgreSQL    FastAPI :8000 (AI Backend)
:5432              │
(users,           ├── Qdrant :6333 (Vector DB)
sessions,         │   (BAAI/bge-m3 embeddings)
messages,         │
documents)        └── Groq API (LLM)
                      (Llama 3.3 70B / Llama 4 Scout)
```

---

## Các chức năng & routes

| # | Chức năng | Route | File |
|---|-----------|-------|------|
| 1 | Landing Page | `/` | `LandingView.vue` |
| 2 | Đăng nhập | `/login` | `LoginView.vue` |
| 3 | Đăng ký | `/register` | `RegisterView.vue` |
| 4 | Chat RAG | `/chat` | `ChatView.vue` |
| 5 | So sánh mô hình | `/compare` | `CompareView.vue` |
| 6 | Evaluation | `/evaluate` | `EvaluationView.vue` |
| 7 | Quản lý Admin | `/admin` | `AdminView.vue` |

---

## Luồng xác thực (Auth Flow)

```
Login Request
    │
    ▼
Spring Boot AuthController
    │ BCrypt verify password
    ▼
PostgreSQL (users table)
    │ Generate JWT
    ▼
Frontend nhận token
    │ Store in localStorage
    ▼
Mọi request tiếp theo: Authorization: Bearer <token>
    │
    ▼
Spring Boot verify JWT → proxy tới FastAPI (nếu cần)
```

---

## Luồng RAG Pipeline

```
Câu hỏi người dùng
    │
    ▼ POST /api/ai/ask
Spring Boot (proxy)
    │
    ▼ POST /ask
FastAPI
    │
    ├─ [1] Guard: Lọc ngoài domain?
    │       └─ Nếu ngoài domain → trả lời từ chối
    │
    ├─ [2] Rewrite: LLM chuẩn hóa câu hỏi
    │
    ├─ [3] Hybrid Search:
    │       ├─ Dense: BAAI/bge-m3 → Qdrant vector search
    │       └─ Sparse: BM25 → Qdrant full-text search
    │
    ├─ [4] Rerank: Xếp hạng top-K chunks
    │
    ├─ [5] Conflict Detector: So sánh các chunk
    │
    ├─ [6] Generator: LLM (Groq Llama) sinh câu trả lời
    │
    └─ [7] Citation: Gán [1][2] vào câu trả lời
    │
    ▼
Response: { answer, citations, rewritten_query, detected_domain }
```

---

## Cơ sở dữ liệu

### PostgreSQL — Schema chính

```sql
-- Bảng users
users (
  id UUID PRIMARY KEY,
  email VARCHAR UNIQUE,
  password_hash VARCHAR,
  role ENUM('user', 'admin'),
  created_at TIMESTAMP
)

-- Bảng chat sessions
chat_sessions (
  id UUID PRIMARY KEY,
  user_id UUID → users.id,
  title TEXT,          -- câu hỏi đầu tiên
  created_at TIMESTAMP
)

-- Bảng messages
chat_messages (
  id UUID PRIMARY KEY,
  session_id UUID → chat_sessions.id,
  role ENUM('user', 'assistant'),
  content TEXT,
  citations JSONB,     -- mảng citation objects
  created_at TIMESTAMP
)

-- Bảng tài liệu pháp luật
legal_documents (
  id UUID PRIMARY KEY,
  law_name TEXT,
  document_code VARCHAR,
  domain VARCHAR,
  effective_date DATE,
  expiry_date DATE,    -- NULL nếu còn hiệu lực
  total_chunks INTEGER,
  file_path TEXT
)
```

### Qdrant — Collection

```
Collection: legal_documents
Vector size: 1024 (BAAI/bge-m3)
Distance: Cosine

Payload per vector:
{
  "chunk_id": "uuid",
  "document_id": "uuid",
  "law_name": "...",
  "article": "Điều 5",
  "clause": "Khoản 8",
  "domain": "giao_thong",
  "content": "...",
  "page_number": 12
}
```

---

## Deployment — Hybrid Mode

```
Docker containers (infrastructure):
  ├── rag-qdrant    (Qdrant :6333)
  └── rag-postgres  (PostgreSQL :5432)

Native processes (applications):
  ├── FastAPI    → backend-python/  (.venv)
  ├── Spring Boot → spring-boot/orchestration-service/ (Maven)
  └── Vue Dev    → frontend-vue/ (npm)
```

**Khởi động:**
```powershell
.\start.ps1       # One-click start tất cả
.\stop.ps1        # Dừng tất cả
.\dev-hybrid.ps1 start   # Chỉ start Docker infra
.\dev-hybrid.ps1 status  # Kiểm tra trạng thái
```

---

## Giới hạn & Lưu ý

| Vấn đề | Chi tiết |
|--------|---------|
| **RAM** | BAAI/bge-m3 cần ~1.4GB RAM khi load |
| **Startup time** | FastAPI cần 3-5 phút để load model |
| **Rate limit** | Groq API có giới hạn token/phút |
| **Offline mode** | `HF_HUB_OFFLINE=1` khi model đã download |
| **OOM** | Dùng Hybrid Mode để tránh Docker OOM |
