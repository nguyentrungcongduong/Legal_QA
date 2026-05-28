# Legal QA — Tài liệu Chức năng

> **Dự án:** Hệ thống Hỏi Đáp Pháp Luật Việt Nam ứng dụng RAG  
> **Stack:** Vue 3 · Spring Boot · FastAPI · Qdrant · PostgreSQL  
> **Cập nhật:** 2026-05-06

---

## Danh sách tài liệu

| # | Chức năng | File | Route |
|---|-----------|------|-------|
| 01 | [Landing Page](./01_landing_page.md) | `LandingView.vue` | `/` |
| 02 | [Đăng nhập & Đăng ký](./02_auth_login_register.md) | `LoginView.vue` / `RegisterView.vue` | `/login`, `/register` |
| 03 | [Chat RAG Tư vấn Pháp luật](./03_chat_rag_qna.md) | `ChatView.vue` | `/chat` |
| 04 | [So sánh Mô hình AI](./04_compare_models.md) | `CompareView.vue` | `/compare` |
| 05 | [Evaluation Dashboard](./05_evaluation_dashboard.md) | `EvaluationView.vue` | `/evaluate` |
| 06 | [Quản lý Admin](./06_admin_management.md) | `AdminView.vue` | `/admin` |
| 07 | [Lịch sử Trò chuyện](./07_chat_history.md) | `ChatHistorySidebar.vue` | (component) |
| 08 | [Document Metadata Drawer](./08_document_metadata_drawer.md) | `DocumentMetadataDrawer.vue` | (component) |
| 09 | [Kiến trúc Hệ thống](./09_system_architecture.md) | — | — |

---

## Tóm tắt nhanh các chức năng

### Dành cho người dùng thường (role: `user`)
- **Landing:** Trang giới thiệu, demo chat, pipeline 7 tầng
- **Login/Register:** Đăng nhập/Đăng ký bằng email + password (JWT)
- **Chat:** Hỏi đáp pháp luật với trích dẫn nguồn, multi-turn, lưu lịch sử
- **Compare:** So sánh Legal RAG vs LLaMA 3.3 vs LLaMA 4 để thấy sự khác biệt
- **Evaluate:** Xem dashboard đánh giá định lượng chống hallucination
- **History:** Xem lại, load lại, xóa các phiên tư vấn cũ

### Dành cho quản trị viên (role: `admin`)
- **Admin > Thống kê:** Tổng quan hệ thống (docs, chunks, users, messages)
- **Admin > Tài liệu:** Upload PDF/DOCX, ingest vào Qdrant, quản lý văn bản
- **Admin > Người dùng:** Xem, đổi role, xóa tài khoản

---

## Khởi động dự án

```powershell
# Yêu cầu: Docker Desktop đang chạy
.\start.ps1

# Truy cập:
# Frontend:  http://localhost:5173
# FastAPI:   http://localhost:8000/docs
# Spring:    http://localhost:8081
# Qdrant:    http://localhost:6333/dashboard
```
