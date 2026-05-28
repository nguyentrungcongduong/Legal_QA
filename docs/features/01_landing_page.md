# 01 · Trang Giới Thiệu (Landing Page)

> **Route:** `/`  
> **File:** `frontend-vue/src/views/LandingView.vue`

---

## Mô tả chức năng

Trang chủ giới thiệu hệ thống **LegalAI RAG** — cửa ngõ đầu tiên người dùng thấy khi truy cập ứng dụng. Hiển thị các thông tin tổng quan, pipeline xử lý, lĩnh vực pháp luật được hỗ trợ và các số liệu hiệu suất của hệ thống.

---

## Các thành phần giao diện

### 1. Navigation Bar (Fixed)
- Logo **LegalAI RAG** + icon dạng tháp luật
- Menu liên kết: **Tính năng**, **Lĩnh vực**, **Hiệu suất**
- Nút **Đăng nhập** → route `/login`
- Sticky top, backdrop-filter blur khi scroll

### 2. Hero Section
- **Badge trạng thái:** "Hệ thống RAG 7 tầng — Đang hoạt động" với dot xanh nhấp nháy
- **Tiêu đề:** "Tư Vấn Pháp Luật Việt Nam Thông Minh"
- **Mô tả:** Giới thiệu kỹ thuật RAG, trích dẫn nguồn
- **CTA Buttons:**
  - `Bắt đầu tư vấn` → `/login`
  - `Tạo tài khoản miễn phí` → `/register`
- **Trust indicators:** ✓ Trích dẫn nguồn · ✓ Không hallucination · ✓ Miễn phí
- **Chat Demo (bên phải):** Mock UI hiển thị ví dụ hỏi đáp thực tế về nồng độ cồn với citation `[1] NĐ 168/2024/NĐ-CP · Điều 10`

### 3. RAG Pipeline Section (`#features`)
7 bước xử lý được hiển thị dạng card với icon SVG:

| Bước | Tên | Chức năng |
|------|-----|-----------|
| 1 | **Guard** | Lọc câu hỏi ngoài domain pháp luật |
| 2 | **Rewrite** | Chuẩn hóa & làm rõ câu hỏi |
| 3 | **Hybrid Search** | Tìm kiếm Dense (vector) + Sparse (BM25) |
| 4 | **Rerank** | Xếp hạng kết quả theo độ liên quan |
| 5 | **Conflict** | Phát hiện xung đột giữa các văn bản luật |
| 6 | **Generate** | LLM sinh câu trả lời tự nhiên |
| 7 | **Citation** | Gán trích dẫn `[1][2]` vào câu trả lời |

### 4. Lĩnh vực pháp luật (`#domains`)
5 lĩnh vực được hỗ trợ hiển thị dạng grid card:

| Icon | Lĩnh vực | Ví dụ |
|------|---------|-------|
| 🚗 | Giao thông | Phạt nồng độ cồn, vượt đèn đỏ... |
| ⚖️ | Hình sự | Tội phạm, hình phạt, tố tụng... |
| 📜 | Dân sự | Hợp đồng, tài sản, thừa kế... |
| 👷 | Lao động | Hợp đồng lao động, sa thải... |
| 💍 | Hôn nhân & Gia đình | Ly hôn, nuôi con, tài sản... |

### 5. Số liệu hiệu suất (`#stats`)
| Chỉ số | Giá trị |
|--------|---------|
| Tầng xử lý RAG | **7** |
| Lĩnh vực pháp luật | **5** |
| Faithfulness Score | **86.7%** |
| Thời gian phản hồi | **< 3s** |

### 6. CTA Section + Footer
- Call-to-action cuối trang dẫn đến trang đăng ký
- Footer với disclaimer: "Thông tin chỉ mang tính tham khảo..."

---

## Thiết kế UI

- **Theme:** Dark mode (`#0a0c10`) với accent màu vàng đồng (`#C9A84C`)
- **Font:** Playfair Display (tiêu đề serif) + Inter (body)
- **Hiệu ứng:** Floating orbs (blur gradient), float animation cho chat demo card
- **Responsive:** 1 cột trên mobile < 900px, chat demo ẩn đi

---

## Liên kết và điều hướng

```
/ (Landing)
├── → /login     (Đăng nhập)
└── → /register  (Đăng ký)
```

---

## Không cần xác thực
Trang này **public** — không cần đăng nhập.
