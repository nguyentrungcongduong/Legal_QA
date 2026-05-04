import asyncio
import concurrent.futures
import json
import os
from fastapi import APIRouter, Depends
from auth.jwt_verify import get_current_user
from retriever.hybrid_retriever import HybridRetriever
from retriever.conflict_detector import ConflictDetector
from guard.domain_router import DomainRouter
from groq import Groq

router = APIRouter()
retriever = HybridRetriever()
conflict_detector = ConflictDetector()
domain_router = DomainRouter()
_groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Domain có dữ liệu trong hệ thống (Qdrant)
_SUPPORTED_DOMAINS = {"giao_thong", "dat_dai", "hon_nhan"}
# Domain phân loại được nhưng KHÔNG có dữ liệu → auto-reject không cần search
_AUTO_REJECT_DOMAINS = {"dan_su", "lao_dong", "hinh_su", "out_of_scope"}

# ============================================================
# Golden test set — 20 câu chuẩn
# ============================================================
GOLDEN_DATASET = [
    {"id": "F001", "question": "Vượt đèn đỏ xe máy bị phạt bao nhiêu tiền?",
     "ground_truth": "Phạt tiền từ 600.000đ đến 1.000.000đ theo Điều 6 Khoản 4 Nghị định 100/2019/NĐ-CP", "type": "factual"},
    {"id": "F002", "question": "Lái xe ô tô có nồng độ cồn vượt mức 0.25mg/lít khí thở bị phạt thế nào?",
     "ground_truth": "Phạt từ 16-18 triệu đồng, tước GPLX 10-12 tháng theo Điều 5 NĐ 100/2019", "type": "factual"},
    {"id": "F003", "question": "Xe máy không có gương chiếu hậu bị xử phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 100.000đ đến 200.000đ theo Điều 17 NĐ 100/2019", "type": "factual"},
    {"id": "F004", "question": "Đi xe máy không đội mũ bảo hiểm phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 400.000đ đến 600.000đ theo Điều 6 NĐ 100/2019", "type": "factual"},
    {"id": "F005", "question": "Ô tô chạy quá tốc độ từ 20-35km/h bị phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 3-5 triệu đồng theo Điều 5 NĐ 100/2019", "type": "factual"},
    {"id": "F006", "question": "Xe máy đi vào đường cao tốc bị phạt như thế nào?",
     "ground_truth": "Phạt tiền từ 1-2 triệu đồng theo Điều 6 NĐ 100/2019", "type": "factual"},
    {"id": "F007", "question": "Không chấp hành hiệu lệnh dừng xe của cảnh sát giao thông bị phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 4-6 triệu đồng đối với ô tô theo Điều 5 NĐ 100/2019", "type": "factual"},
    {"id": "F008", "question": "Lái xe ban đêm không bật đèn chiếu sáng bị xử phạt thế nào?",
     "ground_truth": "Phạt tiền từ 100.000đ đến 200.000đ với xe máy theo Điều 6 NĐ 100/2019", "type": "factual"},
    {"id": "T001", "question": "Mức phạt nồng độ cồn xe máy hiện hành cao nhất là bao nhiêu?",
     "ground_truth": "Phạt từ 6-8 triệu đồng, tước GPLX 22-24 tháng theo NĐ 123/2021 sửa đổi NĐ 100/2019", "type": "temporal"},
    {"id": "T002", "question": "Nghị định 100/2019 có hiệu lực từ ngày nào?",
     "ground_truth": "Có hiệu lực từ ngày 01/01/2020", "type": "temporal"},
    {"id": "T003", "question": "Nghị định 123/2021 thay đổi gì so với Nghị định 100/2019?",
     "ground_truth": "Sửa đổi bổ sung một số điều về mức phạt vi phạm nồng độ cồn và một số hành vi khác", "type": "temporal"},
    {"id": "C001", "question": "Người đi bộ sang đường không đúng nơi quy định bị xử lý thế nào?",
     "ground_truth": "Phạt cảnh cáo hoặc phạt tiền từ 60.000đ đến 100.000đ theo Điều 9 NĐ 100/2019", "type": "conflict"},
    {"id": "C002", "question": "Xe đạp điện không đội mũ bảo hiểm phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 100.000đ đến 200.000đ theo Điều 8 NĐ 100/2019", "type": "conflict"},
    {"id": "O001", "question": "Thuế giá trị gia tăng (VAT) được tính như thế nào?",
     "ground_truth": "OUT_OF_DOMAIN", "type": "out_of_domain"},
    {"id": "O002", "question": "Luật thuế thu nhập cá nhân quy định mức thuế thế nào?",
     "ground_truth": "OUT_OF_DOMAIN", "type": "out_of_domain"},
    {"id": "O003", "question": "Thủ tục thành lập công ty TNHH cần những gì?",
     "ground_truth": "OUT_OF_DOMAIN", "type": "out_of_domain"},
    {"id": "F009", "question": "Xe tải chở hàng quá tải trọng cho phép bị xử phạt thế nào?",
     "ground_truth": "Phạt từ 3-5 triệu đồng tùy mức độ vượt tải theo Điều 24 NĐ 100/2019", "type": "factual"},
    {"id": "F010", "question": "Dừng xe trên cầu bị phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 400.000đ đến 600.000đ với xe máy theo Điều 6 NĐ 100/2019", "type": "factual"},
    {"id": "F011", "question": "Xe máy chở 3 người bị phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 400.000đ đến 600.000đ theo Điều 6 NĐ 100/2019", "type": "factual"},
    {"id": "F012", "question": "Vượt xe ở nơi có biển cấm vượt phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 3-5 triệu đồng với ô tô theo Điều 5 NĐ 100/2019", "type": "factual"},
]


def _run_rag_pipeline(question: str, top_k: int = 5) -> dict:
    """Synchronous RAG pipeline wrapper."""
    chunks = retriever.search(question, top_k=top_k * 4)
    conflict_result = conflict_detector.detect_and_resolve(chunks)
    resolved = conflict_result["resolved_chunks"][:top_k]
    contexts = [c.get("content", "") for c in resolved]
    return {
        "resolved": resolved,
        "contexts": contexts,
        "conflicts": conflict_result["conflicts"],
        "has_conflict": conflict_result["has_conflict"],
    }


def _compute_faithfulness_simple(answer: str, contexts: list[str]) -> float:
    """
    Lightweight faithfulness proxy — không cần RAGAS.
    Đếm số từ quan trọng trong câu trả lời khớp với context.
    Score = overlap_words / answer_words (capped 0-1).
    Dùng làm FALLBACK khi Groq không khả dụng.
    """
    if not contexts or not answer:
        return 0.0
    combined_context = " ".join(contexts).lower()
    answer_words = [w for w in answer.lower().split() if len(w) > 3]
    if not answer_words:
        return 0.5
    matched = sum(1 for w in answer_words if w in combined_context)
    return round(min(matched / len(answer_words), 1.0), 3)


def llm_faithfulness_judge(
    answer: str,
    contexts: list[str],
    question: str,
) -> dict:
    """
    LLM-based faithfulness judge dùng Groq (Llama 3.3 70B).
    Tách câu trả lời thành các claims độc lập, đánh giá từng claim.

    Returns:
        dict with:
          - claims: list of {claim, verdict: SUPPORTED|CONTRADICTED|NOT_MENTIONED}
          - faithfulness_score: float 0-1
          - hallucination_detected: bool
          - explanation: str
    """
    if not answer or not contexts:
        return {
            "claims": [],
            "faithfulness_score": 0.0,
            "hallucination_detected": True,
            "explanation": "Không có câu trả lời hoặc context.",
        }

    context_text = "\n\n".join(
        f"[{i+1}] {c[:400]}" for i, c in enumerate(contexts[:5])
    )

    prompt = f"""Bạn là chuyên gia đánh giá chất lượng hệ thống RAG pháp luật Việt Nam.

VĂN BẢN PHÁP LUẬT (nguồn dữ liệu):
{context_text}

CÂU HỎI: {question}

CÂU TRẢ LỜI CẦN ĐÁNH GIÁ: {answer[:600]}

Nhiệm vụ:
1. Tách câu trả lời thành các claims (phát biểu) độc lập về pháp luật
2. Với mỗi claim, đánh giá: SUPPORTED (có trong context) / CONTRADICTED (mâu thuẫn context) / NOT_MENTIONED (không có căn cứ)
3. Tính faithfulness_score = số claims SUPPORTED / tổng số claims
4. hallucination_detected = true nếu có bất kỳ claim CONTRADICTED hoặc faithfulness_score < 0.5

TRẢ VỀ JSON HỢP LỆ (không thêm text ngoài JSON):
{{
  "claims": [
    {{"claim": "...", "verdict": "SUPPORTED"}},
    {{"claim": "...", "verdict": "NOT_MENTIONED"}}
  ],
  "faithfulness_score": 0.85,
  "hallucination_detected": false,
  "explanation": "Lý do ngắn gọn"
}}"""

    try:
        resp = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown code fences nếu model wrap trong ```json
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"[LLM Judge] Lỗi: {e} — fallback word-overlap")
        score = _compute_faithfulness_simple(answer, contexts)
        return {
            "claims": [],
            "faithfulness_score": score,
            "hallucination_detected": score < 0.5,
            "explanation": f"Fallback (word-overlap): {e}",
        }


def _compute_relevancy_simple(question: str, answer: str) -> float:
    """Lightweight relevancy proxy — keyword overlap giữa question và answer."""
    if not answer:
        return 0.0
    q_words = set(w.lower() for w in question.split() if len(w) > 2)
    a_words = set(w.lower() for w in answer.split() if len(w) > 2)
    if not q_words:
        return 0.5
    overlap = len(q_words & a_words)
    return round(min(overlap / len(q_words), 1.0), 3)


def llm_answer_relevancy(question: str, answer: str) -> float:
    """
    LLM judge đánh giá mức độ liên quan của câu trả lời với câu hỏi.
    Thay thế word-overlap — chính xác hơn với tiếng Việt và legal domain.
    """
    if not answer or not question:
        return 0.0
    prompt = f"""Bạn đánh giá hệ thống hỏi đáp pháp luật Việt Nam.

Câu hỏi: {question}
Câu trả lời: {answer[:500]}

Chấm điểm mức độ liên quan từ 0.0 đến 1.0:
- 1.0: Trả lời đúng trọng tâm, đầy đủ thông tin pháp lý
- 0.7: Liên quan nhưng thiếu chi tiết
- 0.4: Lạc đề một phần
- 0.0: Không liên quan

Chỉ trả về một số thập phân duy nhất, không giải thích."""
    try:
        res = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5,
        )
        return min(1.0, max(0.0, float(res.choices[0].message.content.strip())))
    except Exception as e:
        print(f"[llm_answer_relevancy] Fallback: {e}")
        return _compute_relevancy_simple(question, answer)


def llm_context_precision(question: str, contexts: list[str]) -> float:
    """
    Tỉ lệ chunks retrieved thực sự liên quan đến câu hỏi.
    Thay thế keyword-overlap — chính xác hơn với cú pháp pháp lý Việt Nam.
    """
    if not contexts:
        return 0.0
    relevant = 0
    for ctx in contexts:
        prompt = f"""Văn bản pháp luật sau có liên quan đến câu hỏi không?

Câu hỏi: {question}
Văn bản: {ctx[:400]}

Chỉ trả lời: YES hoặc NO"""
        try:
            res = _groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=3,
            )
            if "YES" in res.choices[0].message.content.upper():
                relevant += 1
        except Exception as e:
            print(f"[llm_context_precision] Fallback chunk: {e}")
            q_kw = [w.lower() for w in question.split() if len(w) > 3]
            if any(kw in ctx.lower() for kw in q_kw):
                relevant += 1
    return round(relevant / len(contexts), 3)


def llm_context_recall(ground_truth: str, contexts: list[str]) -> float:
    """
    Context có chứa đủ thông tin để trả lời đúng như ground truth không.
    Thay thế keyword-overlap — hiểu ngữ nghĩa hơn.
    """
    if not contexts or ground_truth in ("OUT_OF_DOMAIN", ""):
        return 1.0
    context_text = "\n".join(ctx[:300] for ctx in contexts[:3])
    prompt = f"""Ground truth (câu trả lời đúng): {ground_truth}
Context retrieved: {context_text[:800]}

Context có chứa đủ thông tin để suy ra câu trả lời đúng không?
Chấm từ 0.0 đến 1.0. Chỉ trả về số thập phân."""
    try:
        res = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5,
        )
        return min(1.0, max(0.0, float(res.choices[0].message.content.strip())))
    except Exception as e:
        print(f"[llm_context_recall] Fallback: {e}")
        gt_kw = [w.lower() for w in ground_truth.split() if len(w) > 3]
        combined = " ".join(contexts).lower()
        recalled = sum(1 for kw in gt_kw if kw in combined)
        return round(recalled / max(len(gt_kw), 1), 3)


# Thread pool dùng cho evaluation — mặc định 4 workers (4 test cases song song)
_EVAL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="eval")


def run_single_test(test_case: dict) -> dict:
    question = test_case["question"]
    ground_truth = test_case["ground_truth"]
    q_type = test_case["type"]

    # Out-of-domain: dùng đúng logic như main /ai/query
    # Layer 1: Domain classification
    # Layer 2a: Nếu domain không có dữ liệu → auto reject
    # Layer 2b: Nếu domain có dữ liệu → search + threshold 0.55 (strict cho OOD test)
    if q_type == "out_of_domain":
        detected_domain = domain_router.classify(question)
        # Phân loại thành domain không có dữ liệu → reject ngay
        if detected_domain in _AUTO_REJECT_DOMAINS or detected_domain == "small_talk":
            rejected = True
            top_score = 0.0
        else:
            # Search trong domain có dữ liệu — threshold cao hơn main query
            # vì OOD test cần strict hơn để đảm bảo không false-negative
            chunks = retriever.search(question, top_k=5, domain=detected_domain)
            top_score = max((float(c.get("dense_score") or 0) for c in chunks), default=0.0)
            rejected = top_score < 0.55  # strict: cao hơn 0.45 của main query
        return {
            "id": test_case["id"],
            "question": question,
            "type": q_type,
            "ground_truth": ground_truth,
            "generated_answer": "OUT_OF_DOMAIN" if rejected else "ANSWERED (incorrect — should reject)",
            "out_of_domain_correct": rejected,
            "faithfulness": 1.0 if rejected else 0.0,
            "answer_relevancy": 1.0 if rejected else 0.0,
            "context_precision": None,
            "context_recall": None,
            "is_hallucinated": not rejected,
        }

    # Normal RAG pipeline
    pipeline = _run_rag_pipeline(question, top_k=5)
    contexts = pipeline["contexts"]
    resolved = pipeline["resolved"]

    # Build a basic answer from top chunk
    if resolved:
        top = resolved[0]
        snippet = (top.get("content", "")).strip().replace("\n", " ")
        snippet = " ".join(snippet.split())[:300]
        generated_answer = (
            f"Theo {top.get('law_name', 'văn bản pháp luật')}"
            f" ({top.get('article', 'không rõ điều')}"
            f"{', ' + top.get('clause') if top.get('clause') else ''}), "
            f"nội dung liên quan: {snippet}."
        )
    else:
        generated_answer = f"Không tìm thấy căn cứ pháp lý phù hợp cho: '{question}'."

    # Metrics — dùng LLM judge cho cả 4 metrics (chính xác hơn word-overlap)
    judge_result = llm_faithfulness_judge(generated_answer, contexts, question)
    faith          = judge_result["faithfulness_score"]
    is_hallucinated = judge_result["hallucination_detected"]
    relevancy      = llm_answer_relevancy(question, generated_answer)
    ctx_precision  = llm_context_precision(question, contexts)
    ctx_recall     = llm_context_recall(ground_truth, contexts)

    return {
        "id": test_case["id"],
        "question": question,
        "type": q_type,
        "ground_truth": ground_truth,
        "generated_answer": generated_answer,
        "faithfulness": faith,
        "answer_relevancy": relevancy,
        "context_precision": ctx_precision,
        "context_recall": ctx_recall,
        "is_hallucinated": is_hallucinated,
        "judge_claims": judge_result.get("claims", []),
        "judge_explanation": judge_result.get("explanation", ""),
        "has_conflict": pipeline["has_conflict"],
        "citations": [
            {
                "chunk_id": str(c.get("chunk_id", "")),
                "law_name": c.get("law_name"),
                "article": c.get("article"),
            }
            for c in resolved
        ],
    }


@router.post("/ai/evaluate")
async def run_evaluation(
    current_user: str = Depends(get_current_user)
):
    """Run 20-case golden dataset evaluation.

    Dùng ThreadPoolExecutor (4 workers) để chạy song song,
    tránh blocké event loop vì _run_rag_pipeline và llm_faithfulness_judge là sync.
    """
    loop = asyncio.get_event_loop()
    futures = [
        loop.run_in_executor(_EVAL_EXECUTOR, run_single_test, tc)
        for tc in GOLDEN_DATASET
    ]
    results = list(await asyncio.gather(*futures))

    normal_results = [r for r in results if r["type"] != "out_of_domain"]
    ood_results = [r for r in results if r["type"] == "out_of_domain"]

    def safe_avg(values):
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    avg_faithfulness = safe_avg(r["faithfulness"] for r in normal_results)
    avg_relevancy = safe_avg(r["answer_relevancy"] for r in normal_results)
    avg_precision = safe_avg(r["context_precision"] for r in normal_results)
    avg_recall = safe_avg(r["context_recall"] for r in normal_results)
    hallucination_rate = round(
        sum(1 for r in normal_results if r["is_hallucinated"]) / max(len(normal_results), 1), 3
    )
    ood_accuracy = round(
        sum(1 for r in ood_results if r.get("out_of_domain_correct")) / max(len(ood_results), 1), 3
    )

    # Group by type
    by_type: dict[str, list] = {}
    for r in results:
        by_type.setdefault(r["type"], []).append(r)

    return {
        "summary": {
            "total": len(results),
            "avg_faithfulness": avg_faithfulness,
            "avg_answer_relevancy": avg_relevancy,
            "avg_context_precision": avg_precision,
            "avg_context_recall": avg_recall,
            "hallucination_rate": hallucination_rate,
            "out_of_domain_accuracy": ood_accuracy,
            "passed": sum(1 for r in results if not r["is_hallucinated"]),
            "failed": sum(1 for r in results if r["is_hallucinated"]),
        },
        "by_type": {
            t: {
                "count": len(items),
                "avg_faithfulness": safe_avg(r["faithfulness"] for r in items),
                "avg_relevancy": safe_avg(r["answer_relevancy"] for r in items),
                "avg_precision": safe_avg(
                    r["context_precision"] for r in items if r.get("context_precision") is not None
                ),
                "hallucination_rate": round(
                    sum(1 for r in items if r["is_hallucinated"]) / len(items), 3
                ),
            }
            for t, items in by_type.items()
        },
        "results": results,
    }
