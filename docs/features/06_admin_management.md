# 06 · Trang Quản Lý Admin

**Route:** `/admin`
**File backend chính:** `backend-python/routers/admin.py`
**Yêu cầu:** role = `admin` — guard ở cả Vue Router lẫn FastAPI `require_admin`

---

Trang quản trị chia làm 3 tab: Thống kê, Tài liệu, và Người dùng. Chỉ tài khoản có role `admin` mới vào được.

## Tab Tài liệu — Luồng ingest văn bản pháp luật

Đây là cách đưa văn bản pháp luật vào hệ thống để RAG có thể tìm kiếm. Admin điền metadata (tên văn bản, mã, lĩnh vực, ngày hiệu lực), chọn file PDF hoặc DOCX, rồi nhấn "UPLOAD VÀ INGEST".

Backend nhận file và tạo một background job chạy riêng biệt để không block API response:

```python
# admin.py — upload file + dispatch background job
@router.post("/upload-document")
async def upload_document(file: UploadFile, domain: str, law_name: str, ...):
    save_path.write_bytes(content)          # lưu file vào data/raw/
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "progress_pct": 10}
    background_tasks.add_task(_dispatch_ingest, job_id, str(save_path), metadata)
    return {"job_id": job_id}               # trả về ngay để frontend bắt đầu polling
```

Ingest pipeline chạy trong `ThreadPoolExecutor(max_workers=1)` gồm các bước:

**Extract** → đọc toàn bộ text từ PDF/DOCX (`ingestion/ingest.py`)

**Chunking** → thay vì chia theo số ký tự cố định, hệ thống nhận diện cấu trúc "Điều X, Khoản Y" và chia theo đó. Mỗi điều khoản là một đơn vị pháp lý độc lập — nếu cắt giữa chừng sẽ làm mất ngữ nghĩa và RAG sẽ tìm nhầm.

**Embedding** → model BAAI/bge-m3 chạy local tạo vector 1024 chiều cho từng chunk. Không cần gọi API ngoài cho bước này.

**Qdrant** → upsert vectors vào collection `legal_chunks` kèm payload: `domain`, `law_name`, `article`, `clause`, `effective_date`.

**PostgreSQL** → lưu metadata vào bảng `legal_documents`.

```python
# admin.py — ingest runner cập nhật progress theo từng bước
def _run_ingest_sync(job_id, file_path, metadata):
    _jobs[job_id]["progress_pct"] = 30   # extract
    total = ingest_document(file_path, metadata)  # chunk + embed + upsert
    _jobs[job_id].update({"status": "done", "total_chunks": total, "progress_pct": 100})
```

Frontend polling `GET /api/admin/ingest-status/:job_id` mỗi 2 giây để cập nhật thanh tiến trình. Sau khi hoàn tất, văn bản mới ngay lập tức có thể tìm kiếm trong RAG — không cần restart server.

## Kiểm soát truy cập (3 lớp bảo vệ)

```
Lớp 1 — Vue Router: authStore.user.role === 'admin' → nếu không phải admin, redirect /chat
Lớp 2 — FastAPI require_admin: decode JWT → tra PostgreSQL → nếu role != 'admin' → 403
Lớp 3 — Endpoint-level: DELETE /documents/:id dùng Depends(require_admin), không chỉ Depends(get_current_user)
```

```python
# admin.py — endpoint xóa tài liệu chỉ admin mới được
@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, _admin: dict = Depends(require_admin)):
    # require_admin bao gồm cả get_current_user + kiểm tra role
```

## Tab Thống kê

Gọi `GET /api/admin/stats` — FastAPI tra PostgreSQL tổng hợp: số văn bản, tổng chunks, số người dùng, số câu hỏi. Biểu đồ phân bổ chunks theo lĩnh vực giúp admin biết lĩnh vực nào còn thiếu dữ liệu.

## Tab Người dùng

Danh sách tài khoản từ PostgreSQL. Admin nâng/hạ quyền qua `PATCH /api/admin/users/:id/role`. Tài khoản đang đăng nhập bị disable các thao tác này để tránh tự khóa mình.

---

**API chính:** `GET /api/admin/stats` · `POST /api/admin/upload-document` · `GET /api/admin/ingest-status/:job_id` · `DELETE /api/admin/documents/:id` · `PATCH /api/admin/users/:id/role`
