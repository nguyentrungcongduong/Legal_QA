# Legal QA — Kiểm tra độ chính xác tài liệu features/

> Audit ngày 2026-05-09 — đối chiếu tài liệu với code thực tế

---

## ✅ Các file ĐÚNG

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `02_auth_login_register.md` | ✅ OK | Mô tả JWT, BCrypt chuẩn |
| `05_evaluation_dashboard.md` | ✅ OK | Đã dùng LLM-as-a-Judge (không phải RAGAS) |
| `06_admin_management.md` | ✅ OK | 3 tab, pipeline ingest đúng |
| `07_chat_history.md` | ✅ OK | |
| `08_document_metadata_drawer.md` | ✅ OK | |
| `09_system_architecture.md` | ✅ OK | Hybrid mode đúng |

---

## ❌ Chỗ SAI cần sửa

### 1. `03_chat_rag_qna.md` — Endpoint sai
- **Dòng 5-6:** Ghi endpoint là `/ask` và `/api/ai/ask` → **thực tế là `/ai/query` và `/api/ai/query`**
- **Dòng 98:** `POST /api/ai/ask` → sai
- **Dòng 156:** `POST /api/ai/ask` → sai

### 2. `04_compare_models.md` — Response structure sai
- **Dòng 122-123:** Response ghi `vanilla_gpt` / `vanilla_gemini` → **thực tế là `vanilla_llama33` / `vanilla_llama4`** (dùng Groq, không có GPT/Gemini)

### 3. `README.md` — Tóm tắt Compare sai
- **Dòng 31:** Ghi "So sánh Legal RAG vs **LLaMA 3.3 vs LLaMA 4**" — phần này đúng
- Không có vấn đề lớn

