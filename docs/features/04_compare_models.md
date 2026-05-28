# 04 · So Sánh Mô Hình AI (Model Benchmark)

**Route:** `/compare`
**File backend chính:** `backend-python/routers/compare.py` — `POST /ai/compare`

---

Tính năng này cho phép người dùng nhập một câu hỏi pháp luật và xem đồng thời câu trả lời từ **3 mô hình AI** chạy song song — một có RAG, hai không có RAG. Mục đích chính là minh họa trực quan tại sao hệ thống RAG cần thiết trong bài toán pháp luật.

## Luồng hoạt động

Người dùng nhập câu hỏi và nhấn "SO SÁNH". Frontend gọi `POST /api/ai/compare`. FastAPI nhận request và dùng `asyncio.gather()` để khởi chạy **3 coroutine song song**:

```python
# routers/compare.py — 3 task chạy đồng thời
rag_result, llama_result, llama4_result = await asyncio.gather(
    run_rag_pipeline(query),      # Cột 1: Legal RAG đầy đủ pipeline
    call_vanilla_llama(query),    # Cột 2: Llama 3.3 70B không có context
    call_vanilla_gemini(query),   # Cột 3: Llama 4 Scout không có context
)
```

Dùng `asyncio.gather` thay vì gọi tuần tự vì 3 pipeline không phụ thuộc vào nhau — chạy song song giảm thời gian chờ từ ~9s xuống còn ~3s.

## Sự khác biệt kỹ thuật giữa 3 cột

**Cột 1 — Legal RAG** (`run_rag_pipeline`): Chạy Hybrid Search trong Qdrant để lấy context, qua ConflictDetector, rồi mới sinh câu trả lời với context thực tế kèm theo. Kết quả có trích dẫn điều khoản.

```python
# compare.py — RAG pipeline
async def run_rag_pipeline(query: str) -> dict:
    chunks  = retriever.search(query, top_k=20)
    result  = conflict_detector.detect_and_resolve(chunks)
    resolved = result["resolved_chunks"][:5]
    resp = generator.generate(query=query, chunks=resolved, conflicts=result["conflicts"])
    return {**resp, "has_citations": True, "model": "legal-rag"}
```

**Cột 2 & 3 — Vanilla Models** (`call_vanilla_llama`, `call_vanilla_gemini`): Gọi thẳng Groq API chỉ với câu hỏi gốc, **không truyền bất kỳ context nào**. Model trả lời từ kiến thức training, không có trích dẫn, không thể kiểm chứng.

```python
# compare.py — Vanilla: không có context, chỉ có câu hỏi
async def call_vanilla_llama(query: str) -> dict:
    answer = await _groq(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": query},   # ← không có context gì thêm
        ],
    )
    return {"answer": answer, "citations": [], "has_citations": False}
```

## Tại sao Vanilla model nguy hiểm trong bài toán pháp luật?

Khi luật thay đổi — ví dụ NĐ 168/2024 tăng mức phạt vượt đèn đỏ từ 300K lên 18-20 triệu — Vanilla LLM vẫn trả lời theo luật cũ vì training data có cutoff date. Người dùng nhận câu trả lời trông có vẻ đúng nhưng thực ra đã lỗi thời. Legal RAG không có vấn đề này vì chỉ dùng văn bản đã được admin ingest — update NĐ 168/2024 lên là hệ thống biết ngay.

## Fallback khi backend không kết nối

Nếu API không phản hồi, frontend tự động hiển thị mock data cứng để vẫn demo được giao diện 3 cột trong các buổi thuyết trình không có internet ổn định.

---

**API chính:** `POST /api/ai/compare`
Request: `{ "query": "..." }`
Response: `{ rag: { answer, citations, conflicts }, vanilla_gpt: { answer }, vanilla_gemini: { answer } }`
