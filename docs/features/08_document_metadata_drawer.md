# 08 · Document Metadata Drawer & PDF Viewer

**Component:** `frontend-vue/src/components/DocumentMetadataDrawer.vue`
**Dùng trong:** `ChatView.vue`, `CompareView.vue`

---

Khi người dùng nhận câu trả lời từ AI, mỗi câu trả lời đi kèm các citation chip như `[1] Nghị định 168/2024 — Điều 6`. Click vào bất kỳ citation nào, một drawer trượt từ bên phải màn hình hiển thị chi tiết của văn bản pháp luật gốc đó.

## Mục đích

Đây là tính năng "kiểm chứng" — cho phép người dùng xác minh rằng câu trả lời AI không phải bịa mà thực sự có nguồn. Người dùng có thể đọc nguyên văn điều khoản trong văn bản gốc, xem ngày hiệu lực, và biết chính xác đoạn nào trong PDF được dùng để sinh câu trả lời.

## Luồng khi click vào citation — không có extra API call

Điểm quan trọng: **Drawer mở tức thì, không cần fetch thêm dữ liệu.** Toàn bộ thông tin citation đã được trả về cùng response `POST /ai/query` và lưu sẵn trong Vue component state.

```javascript
// ChatView.vue — dữ liệu citation đã sẵn có từ response
function openCitation(citation) {
  toast.legal(`Đang tải bản gốc: ${citation.law_name}`)
  drawerCitation.value = citation   // citation object đã có đủ mọi thứ
  drawerOpen.value = true           // chỉ cần toggle, không cần gọi API
}
```

Mỗi citation object trong response `citations[]` đã chứa đủ:

```json
{
  "law_name": "Nghị định 168/2024/NĐ-CP",
  "article": "Điều 6",
  "clause": "Khoản 9",
  "document_code": "168/2024/ND-CP",
  "effective_date": "2025-01-01",
  "page_number": 12,
  "content": "Người điều khiển xe mô tô, xe gắn máy vi phạm...",  ← text gốc
  "file_path": "data/pdf_store/ND168_2024.pdf"                    ← đường dẫn PDF
}
```

## Hiển thị nội dung văn bản gốc

Drawer ưu tiên hiển thị theo thứ tự: nếu `file_path` tồn tại và PDF có trên server → embed PDF iframe với anchor `#page=12` để nhảy thẳng đến trang chứa điều khoản đó. Nếu không có file PDF → hiển thị `content` (đoạn text chunk đã extract khi ingest).

PDF được serve qua FastAPI static mount:
```python
# main.py
app.mount("/pdf-files", StaticFiles(directory=str(_PDF_DIR)), name="pdfs")
# URL: http://localhost:8000/pdf-files/ND168_2024.pdf#page=12
```

## Tích hợp với CompareView

Ở trang so sánh 3 mô hình, chỉ cột Legal RAG có citation (hai cột Vanilla không retrieve văn bản nên không có). Click vào citation card trong cột RAG cũng mở cùng `DocumentMetadataDrawer` component — dùng chung, không duplicate code.

```vue
<!-- Cùng component dùng ở cả ChatView và CompareView -->
<DocumentMetadataDrawer
  :is-open="drawerOpen"
  :data="drawerCitation"
  @close="drawerOpen = false"
/>
```

---

Đóng drawer bằng nút ✕ hoặc click ra ngoài backdrop. Animation trượt vào từ phải: `transform: translateX(100%)` → `translateX(0)` trong 0.3s.
