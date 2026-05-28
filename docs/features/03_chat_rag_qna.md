# 03 · Chat Tư Vấn Pháp Luật (RAG Q&A)

**Route:** `/chat` — **Backend:** FastAPI `:8000` — `POST /ai/query`
**File điều phối chính:** `backend-python/api/main.py`

---

Đây là tính năng cốt lõi của hệ thống. Người dùng đặt câu hỏi pháp luật bằng ngôn ngữ tự nhiên, hệ thống trả lời dựa hoàn toàn vào **văn bản pháp luật thực tế đã được lưu trữ** — không tự bịa từ bộ nhớ AI. Mọi câu trả lời đều kèm trích dẫn điều khoản cụ thể để người dùng có thể kiểm chứng.

## Luồng từ lúc gửi câu hỏi đến khi có câu trả lời

Khi người dùng nhấn Enter, frontend hiển thị tin nhắn của họ ngay lập tức (không chờ server). Đồng thời, nếu chưa có phiên chat, hệ thống tạo một session mới trên Spring Boot và lưu tin nhắn lên server ngay — để phòng trường hợp mất kết nối giữa chừng. Sau đó frontend gọi `POST /api/ai/query` đến FastAPI với token xác thực. FastAPI chạy toàn bộ RAG pipeline rồi trả về câu trả lời. Frontend hiển thị câu trả lời bằng hiệu ứng typewriter (chữ hiện dần từng ký tự), đồng thời lưu tin nhắn AI lên server.

---

## RAG Pipeline bên trong FastAPI — 5 bước xử lý

### Bước 1 — Phân loại câu hỏi (Domain Router)
**File:** `backend-python/guard/domain_router.py`

Hệ thống nhận dạng câu hỏi thuộc lĩnh vực nào — giao thông, đất đai, lao động, dân sự hay hình sự. Nếu là câu chào hỏi (small talk), hệ thống trả lời ngay mà không cần chạy RAG. Domain được dùng để lọc phạm vi tìm kiếm trong Qdrant, tránh lấy văn bản sai lĩnh vực.

Ưu tiên phân loại: rule-based regex trước (không tốn API), nếu không chắc mới gọi Groq LLM để phán đoán:
```python
# domain_router.py — 3 lớp phân loại
# Lớp 1: Rule-based regex (zero latency, zero cost)
# Lớp 2: Groq Llama 3.3 70B nếu rule không quyết định được
# Lớp 3: Fallback về "giao_thong" (domain mặc định)
domain = domain_router.classify(payload.question, prev_domain=prev_domain)
```

---

### Bước 2 — Viết lại câu hỏi (Query Rewrite)
**File:** `backend-python/guard/query_rewriter.py`

Câu hỏi thô của người dùng thường thiếu chủ thể hoặc mơ hồ, đặc biệt trong hội thoại nhiều lượt. Ví dụ "Còn bị tước bằng không?" — câu này không có ý nghĩa nếu tách riêng. Query Rewriter dùng Groq để viết lại thành câu độc lập: "Vượt đèn đỏ xe máy có bị tước bằng lái không?". Câu hỏi rõ hơn → tìm kiếm chính xác hơn.

```python
# query_rewriter.py — chỉ rewrite nếu có chat_history
# Nếu không có history → giữ nguyên câu gốc (tiết kiệm API call)
rewritten = query_rewriter.rewrite(payload.question, history)
```

Có cache để tránh gọi LLM lặp lại với cùng câu hỏi + lịch sử.

---

### Bước 3 — Hybrid Search (Truy xuất văn bản)
**File:** `backend-python/retriever/hybrid_retriever.py`

Đây là bước tốn nhiều công nhất. Hệ thống tìm kiếm song song bằng 2 cách:

**Dense Search** — dùng BAAI/bge-m3 chạy local để embed câu hỏi thành vector 1024 chiều rồi tìm theo độ tương đồng ngữ nghĩa trong Qdrant. Phù hợp với câu hỏi ngữ nghĩa phức tạp như "trường hợp nào bị tịch thu phương tiện?".

**Sparse Search** — dùng BM25 tìm theo từ khóa từ PostgreSQL (đã cache). Phù hợp với thuật ngữ pháp luật cụ thể như "Điều 6 Khoản 9" hay "NĐ 168/2024" — những thứ Dense Search hay bỏ sót.

Kết quả của hai cách được gộp bằng **RRF (Reciprocal Rank Fusion)** — chunk nào xếp cao ở cả hai cách sẽ được ưu tiên hơn:

```python
# hybrid_retriever.py
dense  = self._dense_search(query, n, domain=domain)   # Qdrant vector search
sparse = self._sparse_search(query, n, domain=domain)  # BM25 keyword search
merged = self._merge_rrf(dense, sparse, n)             # Reciprocal Rank Fusion
result = self._dedupe_by_content(merged, top_k)        # Loại trùng lặp
```

---

### Bước 4 — Phát hiện xung đột (Conflict Detection)
**File:** `backend-python/retriever/conflict_detector.py`

Hệ thống kiểm tra xem các văn bản tìm được có mâu thuẫn nhau không. Ví dụ NĐ 168/2024 và NĐ 100/2019 cùng quy định về vượt đèn đỏ nhưng mức phạt khác nhau. Khi phát hiện xung đột, hệ thống giữ lại văn bản có `effective_date` mới hơn và loại văn bản cũ ra khỏi context trước khi đưa vào LLM. Xung đột được ghi lại và hiển thị cảnh báo trên UI.

Thuật toán phát hiện hoàn toàn bằng Python, không gọi LLM — so sánh keyword pháp lý chung (≥3 từ) + số tiền phạt không trùng nhau giữa hai chunk:

```python
# conflict_detector.py — pure heuristic, không cần LLM
common_legal = (words_a & _LEGAL_KEYWORDS) & (words_b & _LEGAL_KEYWORDS)
if len(common_legal) >= 3:
    nums_a = set(re.findall(r'\d[\d.]+', text_a))
    nums_b = set(re.findall(r'\d[\d.]+', text_b))
    if len(nums_a & nums_b) == 0:  # Không có số tiền nào trùng → CONFLICT
        # Giữ bản có effective_date mới hơn
        newer, older = (a, b) if date_a >= date_b else (b, a)
```

---

### Bước 5 — Sinh câu trả lời (Waterfall LLM)
**File:** `backend-python/generator/generator.py`

LLM nhận context đã lọc + câu hỏi đã rewrite + lịch sử chat rồi sinh câu trả lời. Hệ thống thử lần lượt theo chiến lược Waterfall: Groq Llama-3.3-70b trước (nhanh nhất, miễn phí), nếu bị rate-limit thì fallback sang Gemini 2.0 Flash, rồi OpenAI GPT-4o-mini, cuối cùng mới dùng template cứng offline nếu tất cả đều fail. Mỗi model nhận cùng một prompt và context nên chất lượng không thay đổi nhiều giữa các fallback.

System prompt quy định LLM **chỉ được dùng thông tin trong context** và phải trích dẫn `[số]` cho từng câu khẳng định:

```python
# generator.py — system prompt chống hallucination
"QUY TẮC CHỐNG ẢO GIÁC: CHỈ sử dụng dữ liệu trong các văn bản được cung cấp.
Mỗi thông tin khẳng định PHẢI có trích dẫn [số].
NẾU KHÔNG ĐỦ DỮ LIỆU: chỉ trả lời 'Hệ thống chưa có đủ dữ liệu về trường hợp này.'"
```

---

## Cơ chế từ chối trả lời (Out-of-Domain Guard)
**File:** `backend-python/api/main.py` — dòng 261

Nếu không tìm được văn bản có điểm tương đồng tối thiểu (dense score < 0.45), hệ thống **không sinh câu trả lời** mà từ chối lịch sự. Đây là cơ chế quan trọng để tránh hallucination — thà nói "tôi không biết" còn hơn trả lời sai:

```python
# main.py
SIMILARITY_THRESHOLD = 0.45
if not results or top_score < SIMILARITY_THRESHOLD:
    return QueryResponse(answer="Câu hỏi này nằm ngoài phạm vi tư vấn...", citations=[])
```

---

## Multi-turn (Hội thoại nhiều lượt)

Mỗi request gửi kèm lịch sử chat (tối đa 6 lượt gần nhất). LLM hiểu ngữ cảnh từ các lượt trước, nên người dùng có thể hỏi tiếp mà không cần nhắc lại: "Còn bị tước bằng lái không?" — LLM hiểu đây là hỏi tiếp về xe máy vượt đèn đỏ từ lượt trước. Lịch sử được lưu trên Spring Boot và fetch lại khi cần.

---

**API chính:** `POST /api/ai/query`
Request: `{ question, top_k, chat_history }`
Response: `{ answer, citations, has_conflict, rewritten_query, model_used }`
