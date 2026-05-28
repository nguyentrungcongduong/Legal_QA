# 05 · Evaluation Dashboard (Đánh giá RAG)

**Route:** `/evaluate`
**File backend chính:** `backend-python/routers/evaluate.py` — `POST /evaluate`
**Chỉ admin** mới có quyền truy cập

---

Đây là tính năng để đo lường xem hệ thống RAG đang hoạt động tốt đến đâu — không phải cảm tính mà bằng số liệu cụ thể. Ý tưởng đơn giản: **dùng chính AI để chấm điểm AI**. Một model nhỏ hơn (Llama 3.1 8B) đóng vai giám khảo, đọc câu hỏi, câu trả lời của hệ thống, và đáp án chuẩn đã chuẩn bị sẵn, rồi cho điểm từng tiêu chí từ 0 đến 1.

## Bộ câu hỏi chuẩn (GOLDEN_DATASET) — 20 câu chia 4 loại

Nhóm tự soạn 20 câu hỏi và đáp án chuẩn, hardcode trong `routers/evaluate.py`. Mỗi loại câu hỏi kiểm tra một điểm yếu khác nhau của RAG:

**Factual (8 câu)** — kiểm tra hệ thống có lấy đúng số tiền phạt, đúng điều khoản không. Ví dụ: *"Vượt đèn đỏ xe máy bị phạt bao nhiêu?"* → đáp án chuẩn: *"18-20 triệu theo Điều 6 Khoản 9 NĐ 168/2024"*. Nếu hệ thống trả lời mức phạt cũ (NĐ 100/2019) → điểm thấp.

**Temporal (3 câu)** — kiểm tra hệ thống có ưu tiên luật mới nhất không. Câu hỏi hỏi về "hiện hành", "mới nhất" — hệ thống phải trả lời theo NĐ 168/2024, không được dùng NĐ 100/2019.

**Conflict (2 câu)** — kiểm tra ConflictDetector có hoạt động đúng không. Khi hai văn bản cùng đề cập một hành vi nhưng mức phạt khác nhau, hệ thống phải chọn văn bản mới hơn.

**Out-of-Domain (3 câu)** — kiểm tra hệ thống có từ chối đúng lúc không. Hỏi về thuế VAT, ly hôn, thủ tục công ty — hệ thống phải nói "ngoài phạm vi" thay vì bịa câu trả lời.

```python
# evaluate.py — ví dụ từng loại
{"id": "F001", "question": "Vượt đèn đỏ xe máy bị phạt bao nhiêu?",
 "ground_truth": "18-20 triệu theo Điều 6 Khoản 9 NĐ 168/2024", "type": "factual"},

{"id": "T001", "question": "Mức phạt nồng độ cồn xe máy hiện hành cao nhất là bao nhiêu?",
 "ground_truth": "30-40 triệu theo Điều 6 Khoản 11 NĐ 168/2024", "type": "temporal"},

{"id": "O001", "question": "Thuế VAT được tính như thế nào?",
 "ground_truth": "OUT_OF_DOMAIN", "type": "out_of_domain"},
```

## Luồng chạy đánh giá — tại sao tuần tự và có sleep?

Admin chọn số câu muốn test (4/8/12/20) rồi nhấn "CHẠY ĐÁNH GIÁ". Hệ thống không chạy tất cả cùng lúc mà chạy **lần lượt từng câu, nghỉ 3 giây giữa mỗi câu**.

Lý do: Groq Free Tier chỉ cho phép 6.000 tokens mỗi phút. Một test case tốn khoảng 1.500–2.000 tokens (chạy RAG pipeline + gọi LLM Judge). Nếu chạy song song 20 câu cùng lúc → vượt giới hạn → tất cả trả về lỗi 429 → toàn bộ điểm về 0. Chạy tuần tự chậm hơn nhưng kết quả đáng tin cậy.

```python
# evaluate.py — 1 worker duy nhất, nghỉ 3s giữa mỗi test
_EVAL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1)

def run_single_test(test_case: dict) -> dict:
    time.sleep(3)   # tránh vượt Groq TPM 6.000 tokens/phút
    ...
```

## LLM Judge chấm điểm thế nào — 4 tiêu chí

Sau khi RAG sinh câu trả lời cho một test case, hệ thống gửi một prompt lớn cho Llama 3.1 8B (model nhỏ, nhanh, tiết kiệm token hơn 70B). Prompt đó chứa đủ: câu hỏi gốc, câu trả lời của hệ thống, đáp án chuẩn, và các đoạn văn bản đã retrieve được. Model phải trả về JSON với 4 điểm số:

- **Faithfulness (độ trung thực):** Câu trả lời có dựa trên context retrieve được không, hay bịa thêm thông tin? Điểm 0 nghĩa là hallucinate hoàn toàn.
- **Answer Relevancy (đúng trọng tâm):** Câu trả lời có đúng với điều người dùng hỏi không? Trả lời đúng luật nhưng sai chủ thể (ô tô thay vì xe máy) → điểm thấp.
- **Context Precision (độ chính xác retrieve):** Trong các chunks đã lấy về, có bao nhiêu phần trăm thực sự liên quan đến câu hỏi? Lấy nhiều rác → điểm thấp.
- **Context Recall (độ đầy đủ retrieve):** Context đã lấy về có đủ thông tin để suy ra đáp án chuẩn không? Nếu ground truth nói "Điều 6 Khoản 9" nhưng context không có đoạn đó → điểm thấp.

```python
# evaluate.py — gộp 4 tiêu chí vào 1 API call duy nhất
def llm_all_metrics(question, answer, contexts, ground_truth) -> dict:
    prompt = f"""
CÂU HỎI: {question}
CÂU TRẢ LỜI: {answer}
GROUND TRUTH: {ground_truth}
CONTEXT RETRIEVED: {ctx_text}

Trả về JSON với 4 điểm từ 0.0 đến 1.0:
faithfulness, answer_relevancy, context_precision, context_recall"""
    resp = _groq_client.chat.completions.create(model="llama-3.1-8b-instant", ...)
```

Gộp 4 tiêu chí vào 1 lần gọi thay vì 4 lần riêng — giảm 75% lượng token tiêu thụ.

## Khi LLM Judge bị rate-limit — Fallback tự động

Nếu Groq trả về lỗi 429 giữa chừng, hệ thống không báo lỗi mà tự động chuyển sang tính điểm bằng cách đếm từ khóa chung. Ít chính xác hơn nhưng vẫn cho ra số liệu thay vì để bảng rỗng.

## Câu hỏi Out-of-Domain — không cần Judge

Với loại câu hỏi ngoài phạm vi (thuế, ly hôn, công ty...), không cần gọi Judge. Hệ thống chỉ kiểm tra một điều duy nhất: vector similarity score khi search có dưới ngưỡng 0.55 không? Nếu có → hệ thống đã từ chối đúng → điểm Faithfulness = 1.0. Nếu hệ thống vẫn trả lời → Faithfulness = 0.0 (đây là hallucination nghiêm trọng).

---

**API chính:** `POST /api/ai/evaluate?count=8`
Response: `{ summary: { avg_faithfulness, hallucination_rate, ... }, by_type: { factual, temporal, ... }, results: [...] }`
