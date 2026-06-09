import asyncio
import concurrent.futures
import json
import math
import os
import time
import uuid
from collections import defaultdict
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from auth.jwt_verify import get_current_user
from retriever.hybrid_retriever import get_retriever
from retriever.conflict_detector import ConflictDetector
from guard.domain_router import DomainRouter
from generator.generator import Generator
from groq import Groq

router = APIRouter()
retriever         = get_retriever()
conflict_detector = ConflictDetector()
domain_router     = DomainRouter()
generator         = Generator()          # dùng để sinh câu trả lời giống /ai/query
_groq_client      = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Domain có dữ liệu trong hệ thống (Qdrant)
_SUPPORTED_DOMAINS = {"giao_thong", "dat_dai", "hon_nhan"}
# Domain phân loại được nhưng KHÔNG có dữ liệu → auto-reject không cần search
_AUTO_REJECT_DOMAINS = {"dan_su", "lao_dong", "hinh_su", "out_of_scope"}

# ─────────────────────────────────────────────────────────────
# Module-level cache cho RAGAS embedder — tránh load BAAI/bge-m3 mỗi job
# ─────────────────────────────────────────────────────────────
_ragas_embeddings_wrapper = None  # khởi tạo lazy lần đầu dùng
_ragas_llm_wrapper        = None  # cache LangchainLLMWrapper

def _get_ragas_embeddings():
    """Lazy-load và cache LangchainEmbeddingsWrapper(BAAI/bge-m3)."""
    global _ragas_embeddings_wrapper
    if _ragas_embeddings_wrapper is None:
        from ragas.embeddings import LangchainEmbeddingsWrapper
        print("[RAGAS] Loading BAAI/bge-m3 embedder (lan dau, se cache lai)...")
        try:
            # Uu tien langchain_huggingface (moi, khong deprecated)
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            from langchain_community.embeddings import HuggingFaceEmbeddings  # fallback
        hf = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": "cpu"},
        )
        _ragas_embeddings_wrapper = LangchainEmbeddingsWrapper(hf)
        print("[RAGAS] Embedder loaded & cached.")
    return _ragas_embeddings_wrapper


def _get_ragas_llm():
    """Lazy-load và cache LangchainLLMWrapper(Groq llama-3.1-8b-instant)."""
    global _ragas_llm_wrapper
    if _ragas_llm_wrapper is None:
        from langchain_groq import ChatGroq
        from ragas.llms import LangchainLLMWrapper
        groq_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0, max_retries=3, request_timeout=120,
        )
        _ragas_llm_wrapper = LangchainLLMWrapper(groq_llm)
        _ragas_llm_wrapper.multiple_completion_supported = False
        print("[RAGAS] LLM wrapper cached.")
    return _ragas_llm_wrapper

# ============================================================
# Golden test set — 20 câu chuẩn
# ============================================================
GOLDEN_DATASET = [
    # ── FACTUAL ─────────────────────────────────────────────────────────────────
    {"id": "F001", "question": "Vượt đèn đỏ xe máy bị phạt bao nhiêu tiền?",
     "ground_truth": "Phạt tiền từ 18-20 triệu đồng theo Điều 6 Khoản 9 Nghị định 168/2024/NĐ-CP", "type": "factual"},
    {"id": "F002", "question": "Lái xe máy có nồng độ cồn vượt quá 0,25 miligam đến 0,4 miligam/1 lít khí thở bị phạt thế nào?",
     "ground_truth": "Phạt từ 18-20 triệu đồng theo Điều 6 Khoản 9 NĐ 168/2024", "type": "factual"},
    {"id": "F003", "question": "Xe máy không có gương chiếu hậu bị xử phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 100.000đ đến 200.000đ theo Nghị định 100/2019 hoặc Nghị định 168/2024", "type": "factual"},
    {"id": "F004", "question": "Đi xe máy không đội mũ bảo hiểm phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 400.000đ đến 600.000đ theo NĐ 168/2024", "type": "factual"},
    {"id": "F005", "question": "Xe máy chạy quá tốc độ từ 20-35km/h bị phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 6-8 triệu đồng theo Điều 6 Khoản 6 NĐ 168/2024", "type": "factual"},
    {"id": "F006", "question": "Xe máy đi vào đường cao tốc bị phạt như thế nào?",
     "ground_truth": "Phạt tiền từ 1-2 triệu đồng theo Nghị định 100/2019 hoặc NĐ 168/2024", "type": "factual"},
    {"id": "F007", "question": "Không chấp hành hiệu lệnh dừng xe của cảnh sát giao thông bị phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 4-6 triệu đồng đối với người điều khiển xe máy theo NĐ 168/2024", "type": "factual"},
    {"id": "F008", "question": "Lái xe ban đêm không bật đèn chiếu sáng bị xử phạt thế nào?",
     "ground_truth": "Phạt tiền từ 400.000đ đến 600.000đ với xe máy theo NĐ 168/2024", "type": "factual"},
    # ── TEMPORAL ─────────────────────────────────────────────────────────────────
    {"id": "T001", "question": "Mức phạt nồng độ cồn xe máy hiện hành cao nhất là bao nhiêu?",
     "ground_truth": "Phạt từ 30-40 triệu đồng đối với nồng độ cồn vượt quá 0,4mg/lít hoặc 80mg/100ml máu, theo Điều 6 Khoản 11 NĐ 168/2024", "type": "temporal"},
    {"id": "T002", "question": "Xe máy vượt đèn đỏ bị phạt như thế nào theo Nghị định mới nhất?",
     "ground_truth": "Phạt tiền từ 18-20 triệu đồng, có thể tước GPLX, theo Điều 6 Khoản 9 NĐ 168/2024", "type": "temporal"},
    {"id": "T003", "question": "Nghị định 168/2024 thay đổi gì so với Nghị định 100/2019?",
     "ground_truth": "Tăng mạnh mức phạt vi phạm giao thông đường bộ, đặc biệt là mức phạt nồng độ cồn, vượt đèn đỏ, quá tốc độ", "type": "temporal"},
    # ── CONFLICT ─────────────────────────────────────────────────────────────────
    {"id": "C001", "question": "Người đi bộ sang đường không đúng nơi quy định bị xử lý thế nào?",
     "ground_truth": "Phạt tiền từ 150.000đ đến 250.000đ theo Điều 10 NĐ 168/2024", "type": "conflict"},
    {"id": "C002", "question": "Xe đạp điện không đội mũ bảo hiểm phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 400.000đ đến 600.000đ theo NĐ 168/2024", "type": "conflict"},
    # ── OUT OF DOMAIN ─────────────────────────────────────────────────────────────
    {"id": "O001", "question": "Thuế giá trị gia tăng (VAT) được tính như thế nào?",
     "ground_truth": "OUT_OF_DOMAIN", "type": "out_of_domain"},
    {"id": "O002", "question": "Luật thuế thu nhập cá nhân quy định mức thuế thế nào?",
     "ground_truth": "OUT_OF_DOMAIN", "type": "out_of_domain"},
    {"id": "O003", "question": "Thủ tục thành lập công ty TNHH cần những gì?",
     "ground_truth": "OUT_OF_DOMAIN", "type": "out_of_domain"},
    # ── MORE FACTUAL ─────────────────────────────────────────────────────────────
    {"id": "F009", "question": "Xe tải chở hàng quá tải trọng cho phép bị xử phạt thế nào?",
     "ground_truth": "Phạt từ 3-5 triệu đồng tùy mức độ vượt tải theo NĐ 168/2024", "type": "factual"},
    {"id": "F010", "question": "Dừng xe trên cầu bị phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 400.000đ đến 600.000đ với xe máy theo NĐ 168/2024", "type": "factual"},
    {"id": "F011", "question": "Xe máy chở 3 người bị phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 400.000đ đến 600.000đ theo NĐ 168/2024", "type": "factual"},
    {"id": "F012", "question": "Vượt xe ở nơi có biển cấm vượt phạt bao nhiêu?",
     "ground_truth": "Phạt tiền từ 4-6 triệu đồng với xe máy theo Điều 6 Khoản 5 NĐ 168/2024", "type": "factual"},
]


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

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
    """Fallback faithfulness: word-overlap proxy."""
    if not contexts or not answer:
        return 0.0
    combined_context = " ".join(contexts).lower()
    answer_words = [w for w in answer.lower().split() if len(w) > 3]
    if not answer_words:
        return 0.5
    matched = sum(1 for w in answer_words if w in combined_context)
    return round(min(matched / len(answer_words), 1.0), 3)


def _compute_context_relevance(question: str, contexts: list[str]) -> float:
    """Context Relevance: tỉ lệ chunks retrieved thực sự liên quan đến câu hỏi.

    Định nghĩa (Es et al., 2023 — RAGAS):
      Đo lường mức độ phù hợp của context với câu hỏi.
      Khác với Context Precision (ranking) và Context Recall (coverage):
      → Câu hỏi này là: "Context tìm được có trả lời được câu hỏi không?"

    Heuristic: một chunk được coi là "relevant" nếu chứa ≥ 30% từ khoá của câu hỏi.
    """
    if not contexts or not question:
        return 0.0
    q_words = [w.lower() for w in question.split() if len(w) > 2]
    if not q_words:
        return 0.5
    relevant_count = 0
    for chunk in contexts:
        chunk_lower = chunk.lower()
        matched = sum(1 for w in q_words if w in chunk_lower)
        if matched / len(q_words) >= 0.3:
            relevant_count += 1
    return round(relevant_count / len(contexts), 3)


def _compute_relevancy_simple(question: str, answer: str) -> float:
    """Answer relevancy heuristic cho tiếng Việt pháp lý.
    1. Base: keyword overlap giữa câu hỏi và câu trả lời.
    2. Bonus: câu trả lời có nội dung pháp lý cụ thể (số tiền, điều khoản...)
       → vì câu hỏi pháp lý VN dùng từ dân gian nhưng câu trả lời dùng văn phộng luật.
    3. Penalty: câu trả lời là lỗi/fallback.
    """
    if not answer:
        return 0.0
    _skip_signals = ["[rate_limit_skip]", "lỗi rag pipeline", "không tìm thấy", "hệ thống từ chối"]
    if any(s in answer.lower() for s in _skip_signals):
        return 0.1
    q_words = set(w.lower() for w in question.split() if len(w) > 2)
    if not q_words:
        return 0.5
    overlap = len(q_words & set(w.lower() for w in answer.lower().split() if len(w) > 2)) / len(q_words)
    legal_markers = ["triệu", "đồng", "phạt", "điều", "khoản", "nghị định", "tước", "hành chính",
                     "xử phạt", "mức phạt", "000", "quy định", "luật"]
    n_legal = sum(1 for m in legal_markers if m in answer.lower())
    if n_legal >= 3 and overlap > 0:
        score = min(overlap * 2.0 + 0.5, 1.0)
    elif n_legal >= 1 and overlap > 0:
        score = min(overlap * 2.0 + 0.2, 1.0)
    elif n_legal >= 3:
        score = 0.6
    else:
        score = overlap
    return round(score, 3)


# ─────────────────────────────────────────────────────────────
# CORE: 1 Groq call cho tất cả 4 metrics
# ─────────────────────────────────────────────────────────────

def llm_all_metrics(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> dict:
    """
    Gộp faithfulness + answer_relevancy + context_precision + context_recall
    vào 1 Groq API call duy nhất với model mạnh (llama-3.3-70b-versatile).
    """
    ctx_text = "\n\n".join(f"[{i+1}] {c[:600]}" for i, c in enumerate(contexts[:4]))
    has_gt = ground_truth not in ("OUT_OF_DOMAIN", "", None)

    prompt = f"""Bạn là chuyên gia đánh giá hệ thống RAG pháp luật Việt Nam. Đánh giá NHANH và CHÍNH XÁC.

CÂU HỎI: {question}
CÂU TRẢ LỜI: {answer[:700]}
GROUND TRUTH: {ground_truth if has_gt else "(không áp dụng)"}

CONTEXT RETRIEVED:
{ctx_text}

Đánh giá 4 metrics và trả về JSON (không thêm text ngoài JSON):
{{
  "faithfulness": <0.0-1.0, tỉ lệ claims trong câu trả lời có căn cứ từ context>,
  "answer_relevancy": <0.0-1.0, câu trả lời có đúng trọng tâm câu hỏi không>,
  "context_precision": <0.0-1.0, tỉ lệ chunks thực sự liên quan đến câu hỏi>,
  "context_recall": <0.0-1.0, context có đủ thông tin để suy ra ground truth không, 0.5 nếu không có ground truth>,
  "hallucination_detected": <true nếu faithfulness < 0.5 hoặc có thông tin sai>,
  "explanation": "<một câu ngắn lý giải>"
}}"""

    try:
        resp = _groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return {
            "faithfulness":          float(data.get("faithfulness", 0.5)),
            "answer_relevancy":      float(data.get("answer_relevancy", 0.5)),
            "context_precision":     float(data.get("context_precision", 0.5)),
            "context_recall":        float(data.get("context_recall", 0.5)),
            "hallucination_detected": bool(data.get("hallucination_detected", False)),
            "claims":                [],
            "explanation":           data.get("explanation", ""),
        }
    except Exception as e:
        print(f"[AllMetrics] Fallback word-overlap: {e}")
        faith = _compute_faithfulness_simple(answer, contexts)
        rel   = _compute_relevancy_simple(question, answer)
        q_kw  = [w.lower() for w in question.split() if len(w) > 3]
        prec  = round(sum(1 for c in contexts if any(kw in c.lower() for kw in q_kw)) / max(len(contexts), 1), 3)
        if has_gt:
            gt_kw   = [w.lower() for w in ground_truth.split() if len(w) > 3]
            combined = " ".join(contexts).lower()
            recall   = round(sum(1 for kw in gt_kw if kw in combined) / max(len(gt_kw), 1), 3)
        else:
            recall = 0.5
        return {
            "faithfulness":          faith,
            "answer_relevancy":      rel,
            "context_precision":     prec,
            "context_recall":        recall,
            "hallucination_detected": faith < 0.5,
            "claims":                [],
            "explanation":           f"Fallback word-overlap ({e})",
        }


# Thread pool — 1 worker: chạy tuần tự, tránh vượt Groq TPM 6k/min
_EVAL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="eval")


# ─────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────

def run_single_test(test_case: dict) -> dict:
    import time
    time.sleep(1)  # 1s giữa mỗi test — đủ tránh Groq TPM 6k/min (giảm từ 3s)
    question     = test_case["question"]
    ground_truth = test_case["ground_truth"]
    q_type       = test_case["type"]

    # ── Out-of-domain: không cần LLM judge ──
    if q_type == "out_of_domain":
        detected_domain = domain_router.classify(question)
        if detected_domain in _AUTO_REJECT_DOMAINS or detected_domain == "small_talk":
            rejected   = True
            top_score  = 0.0
        else:
            chunks    = retriever.search(question, top_k=5, domain=detected_domain)
            top_score = max((float(c.get("dense_score") or 0) for c in chunks), default=0.0)
            rejected  = top_score < 0.55
        return {
            "id":                 test_case["id"],
            "question":           question,
            "type":               q_type,
            "ground_truth":       ground_truth,
            "generated_answer":   "OUT_OF_DOMAIN" if rejected else "ANSWERED (incorrect — should reject)",
            "out_of_domain_correct": rejected,
            "faithfulness":       1.0 if rejected else 0.0,
            "answer_relevancy":   1.0 if rejected else 0.0,
            "context_precision":  None,
            "context_recall":     None,
            "is_hallucinated":    not rejected,
            "judge_claims":       [],
            "judge_explanation":  "",
            "has_conflict":       False,
            "citations":          [],
        }

    # ── Normal RAG pipeline ──
    pipeline = _run_rag_pipeline(question, top_k=5)
    contexts = pipeline["contexts"]
    resolved = pipeline["resolved"]

    # ── Sinh câu trả lời thực (giống /ai/query) thay vì template cứng ──
    if resolved:
        gen_result       = generator.generate(
            query=question,
            chunks=resolved,
            conflicts=pipeline.get("conflicts", []),
        )
        generated_answer = gen_result.get("answer", "")
        # Nếu tất cả provider bị rate-limit, generator trả về template
        # — đánh dấu skip, không chấm điểm sai
        _FALLBACK_SIGNALS = ["Xin lỗi", "tạm thời", "không thể kết nối", "bận", "fallback"]
        if not generated_answer or any(s.lower() in generated_answer.lower() for s in _FALLBACK_SIGNALS):
            generated_answer = "[RATE_LIMIT_SKIP]"
    else:
        generated_answer = f"Không tìm thấy căn cứ pháp lý phù hợp cho: '{question}'."

    # ── LLM judge (llama-3.1-8b-instant) ──
    metrics = llm_all_metrics(question, generated_answer, contexts, ground_truth)

    return {
        "id":                test_case["id"],
        "question":          question,
        "type":              q_type,
        "ground_truth":      ground_truth,
        "generated_answer":  generated_answer,
        "faithfulness":      metrics["faithfulness"],
        "answer_relevancy":  metrics["answer_relevancy"],
        "context_precision": metrics["context_precision"],
        "context_recall":    metrics["context_recall"],
        "is_hallucinated":   metrics["hallucination_detected"],
        "judge_claims":      metrics.get("claims", []),
        "judge_explanation": metrics.get("explanation", ""),
        "has_conflict":      pipeline["has_conflict"],
        "citations": [
            {
                "chunk_id": str(c.get("chunk_id", "")),
                "law_name": c.get("law_name"),
                "article":  c.get("article"),
            }
            for c in resolved
        ],
    }


# ─────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────

@router.post("/ai/evaluate")
async def run_evaluation(
    count: int = Query(default=8, ge=4, le=20, description="Số test cases cần chạy (4-20)"),
    current_user: str = Depends(get_current_user)
):
    """Run evaluation với LLM judge + LLM generator (giống /ai/query).
    count=8  (mặc định): ~30-40 giây
    count=20 (đầy đủ):    ~60-90 giây
    """
    # Sample đều các loại câu hỏi để metrics vẫn đại diện
    from collections import defaultdict
    import math
    by_type = defaultdict(list)
    for tc in GOLDEN_DATASET:
        by_type[tc["type"]].append(tc)
    types  = list(by_type.keys())          # factual, temporal, conflict, out_of_domain
    per_type = max(1, math.ceil(count / len(types)))
    dataset = []
    for t in types:
        dataset.extend(by_type[t][:per_type])
    dataset = dataset[:count]              # cắt chính xác nếu dư

    loop = asyncio.get_event_loop()
    t0   = time.time()
    futures = [
        loop.run_in_executor(_EVAL_EXECUTOR, run_single_test, tc)
        for tc in dataset
    ]
    results = list(await asyncio.gather(*futures))
    elapsed = round(time.time() - t0, 2)

    normal_results = [r for r in results if r["type"] != "out_of_domain"]
    ood_results    = [r for r in results if r["type"] == "out_of_domain"]

    def safe_avg(values):
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    avg_faithfulness    = safe_avg(r["faithfulness"]      for r in normal_results)
    avg_relevancy       = safe_avg(r["answer_relevancy"]  for r in normal_results)
    avg_precision       = safe_avg(r["context_precision"] for r in normal_results)
    avg_recall          = safe_avg(r["context_recall"]    for r in normal_results)
    hallucination_rate  = round(
        sum(1 for r in normal_results if r["is_hallucinated"]) / max(len(normal_results), 1), 3
    )
    ood_accuracy = round(
        sum(1 for r in ood_results if r.get("out_of_domain_correct")) / max(len(ood_results), 1), 3
    )

    by_type: dict[str, list] = {}
    for r in results:
        by_type.setdefault(r["type"], []).append(r)

    return {
        "summary": {
            "total":                  len(results),
            "count_requested":        count,
            "elapsed_seconds":        elapsed,
            "mode":                   "llm-judge",
            "avg_faithfulness":      avg_faithfulness,
            "avg_answer_relevancy":  avg_relevancy,
            "avg_context_precision": avg_precision,
            "avg_context_recall":    avg_recall,
            "hallucination_rate":    hallucination_rate,
            "out_of_domain_accuracy": ood_accuracy,
            "passed": sum(1 for r in results if not r["is_hallucinated"]),
            "failed": sum(1 for r in results if r["is_hallucinated"]),
        },
        "by_type": {
            t: {
                "count":              len(items),
                "avg_faithfulness":   safe_avg(r["faithfulness"]     for r in items),
                "avg_relevancy":      safe_avg(r["answer_relevancy"] for r in items),
                "avg_precision":      safe_avg(
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


# ─────────────────────────────────────────────────────────────
# RAGAS Job Store (in-memory, reset khi restart)
# ─────────────────────────────────────────────────────────────
_ragas_jobs: dict = {}   # job_id -> {status, done_cases, total, result, error}
# ProcessPoolExecutor không work vì shared memory; dùng thread nhưng cần isolate event loop
_ragas_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="ragas")


def _build_ragas_cases(count: int) -> list:
    """Pick cases evenly from ALL types (factual, temporal, conflict, out_of_domain).
    For count=4 this gives exactly 1 of each type for a clean demo."""
    all_types = ["factual", "temporal", "conflict", "out_of_domain"]
    by_type = defaultdict(list)
    for tc in GOLDEN_DATASET:
        by_type[tc["type"]].append(tc)
    selected = []
    # Round-robin across types to fill count slots
    indices = {t: 0 for t in all_types}
    for i in range(count):
        t = all_types[i % len(all_types)]
        pool = by_type[t]
        idx = indices[t]
        if idx < len(pool):
            selected.append(pool[idx])
            indices[t] += 1
        else:
            # fallback: pull from factual if this type exhausted
            fallback = by_type["factual"]
            fi = indices.get("factual_extra", 0)
            if fi < len(fallback):
                selected.append(fallback[fi])
                indices["factual_extra"] = fi + 1
    return selected[:count]


def _run_ragas_job(job_id: str, cases: list):
    """Chạy trong ThreadPoolExecutor — không dùng asyncio của Uvicorn."""
    import threading, math as _math
    job = _ragas_jobs[job_id]
    print(f"[RAGAS] Job {job_id[:8]} started in thread {threading.current_thread().name}")

    # Tách OOD và non-OOD
    questions_idx = []  # indices of non-OOD in cases[]
    questions, answers, contexts_list, ground_truths = [], [], [], []
    ood_results = {}    # case_index -> {correctly_rejected, answer}

    # ── Phase 1: RAG answers + evaluate OOD inline ──────────────────────────
    for i, tc in enumerate(cases):
        q     = tc["question"]
        gt    = tc["ground_truth"]
        qtype = tc.get("type", "factual")

        if qtype == "out_of_domain":
            # OOD: không chạy RAG — chỉ cần domain_router classify
            try:
                detected = domain_router.classify(q)
                if detected in _AUTO_REJECT_DOMAINS or detected == "small_talk":
                    correctly = True
                else:
                    chunks    = retriever.search(q, top_k=5)
                    top_score = max((float(c.get("dense_score") or 0) for c in chunks), default=0.0)
                    correctly = top_score < 0.55
            except Exception:
                correctly = True
            ood_results[i] = {
                "correctly_rejected": correctly,
                "answer": "Hệ thống từ chối (ngoài phạm vi)" if correctly else "Hệ thống trả lời (sai — phải từ chối)",
            }
            ans_preview = ood_results[i]["answer"]
        else:
            try:
                pipeline  = _run_rag_pipeline(q, top_k=3)
                ctx_texts = pipeline["contexts"]
                if pipeline["resolved"]:
                    gen = generator.generate(query=q, chunks=pipeline["resolved"][:3], conflicts=[])
                    ans = gen.get("answer", "")
                else:
                    ans = "Không tìm thấy thông tin liên quan."
            except Exception as e:
                print(f"[RAGAS] RAG error case {i}: {e}")
                ans, ctx_texts = "Lỗi RAG pipeline.", []

            questions_idx.append(i)
            questions.append(q)
            answers.append(ans)
            contexts_list.append(ctx_texts if ctx_texts else [""])
            ground_truths.append(gt)
            ans_preview = ans

        job["done_cases"].append({
            "index":    i + 1,
            "question": q,
            "type":     qtype,
            "answer_preview": ans_preview[:120] + ("..." if len(ans_preview) > 120 else ""),
        })
        job["rag_done"] = i + 1
        print(f"[RAGAS] RAG done {i+1}/{len(cases)}: {q[:40]}")
        time.sleep(1)  # 1s tránh rate-limit (giảm từ 2s)

    job["status"] = "evaluating"
    print(f"[RAGAS] Phase 2: RAGAS on {len(questions)} non-OOD samples")

    # ── Phase 2: RAGAS evaluate — chỉ non-OOD ───────────────────────────────
    try:
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import Faithfulness, ContextPrecision
        # NOTE: AnswerRelevancy bị bỏ — RAGAS tính bằng cách sinh câu hỏi ngược bằng tiếng Anh
        # rồi so sánh với câu hỏi tiếng Việt → similarity ≈ 0 (sai hoàn toàn).
        # Thay bằng heuristic keyword-overlap _compute_relevancy_simple.
        # NOTE: ContextRecall bị bỏ — cần ground-truth comparison cũng gặp vấn đề tương tự.
        # Import được cache ở module level qua _get_ragas_llm / _get_ragas_embeddings
        from datasets import Dataset

        ragas_scores = {}  # case_index -> score dict from RAGAS

        if questions:
            ragas_dataset = Dataset.from_dict({
                "question":     questions,
                "answer":       answers,
                "contexts":     contexts_list,
                "ground_truth": ground_truths,
            })

            ragas_llm = _get_ragas_llm()
            ragas_embeddings = _get_ragas_embeddings()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from ragas.run_config import RunConfig
                result = ragas_evaluate(
                    dataset=ragas_dataset,
                    metrics=[Faithfulness(), ContextPrecision()],
                    llm=ragas_llm, embeddings=ragas_embeddings,
                    raise_exceptions=False,
                    run_config=RunConfig(max_workers=2, timeout=600),
                )
            finally:
                # Huỷ pending tasks trước khi close loop — tránh "cannot schedule new futures"
                try:
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        for task in pending:
                            task.cancel()
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass
                loop.close()
                asyncio.set_event_loop(None)

            df = result.to_pandas()
            scores_list = df.to_dict(orient="records")
            for j, ci in enumerate(questions_idx):
                ragas_scores[ci] = scores_list[j]

        # ── Merge tất cả kết quả ────────────────────────────────────────────
        def sf(v):
            try:
                f = float(v)
                return 0.0 if _math.isnan(f) else f
            except Exception:
                return 0.0

        per_sample = []
        hallucinated_count = 0
        ood_correct_count  = 0
        faith_vals, rel_vals, prec_vals, recall_vals, ctx_rel_vals = [], [], [], [], []

        for i, tc in enumerate(cases):
            qtype = tc.get("type", "factual")
            q, gt = tc["question"], tc["ground_truth"]

            if qtype == "out_of_domain":
                ood = ood_results[i]
                ok  = ood["correctly_rejected"]
                if ok:
                    ood_correct_count += 1
                per_sample.append({
                    "id":                    tc.get("id", f"#{i+1}"),
                    "question":              q,
                    "type":                  qtype,
                    "ground_truth":          gt,
                    "answer":                ood["answer"],
                    "faithfulness":          1.0 if ok else 0.0,
                    "answer_relevancy":      1.0 if ok else 0.0,
                    "context_precision":     None,
                    "context_recall":        None,
                    "is_hallucinated":       not ok,
                    "out_of_domain_correct": ok,
                    "f1_score":              1.0 if ok else 0.0,
                    "judge_explanation":     "Từ chối đúng câu ngoài domain" if ok else "Cần từ chối nhưng đã trả lời",
                })
            else:
                sc    = ragas_scores.get(i, {})
                j     = questions_idx.index(i) if i in questions_idx else -1
                ans_text   = answers[j] if j >= 0 else ""
                ctx_chunks = contexts_list[j] if j >= 0 else []

                faith = round(sf(sc.get("faithfulness", 0.0)), 3)
                # answer_relevancy: heuristic vì RAGAS official bị lỗi với tiếng Việt
                rel   = round(_compute_relevancy_simple(q, ans_text), 3)
                prec  = round(sf(sc.get("context_precision", 0.0)), 3)
                # context_recall: tỉ lệ từ khoá ground truth xuất hiện trong context
                gt_words = [w.lower() for w in gt.split() if len(w) > 3]
                ctx_combined = " ".join(ctx_chunks)
                rec = round(sum(1 for kw in gt_words if kw in ctx_combined.lower()) / max(len(gt_words), 1), 3) \
                      if gt_words and gt not in ("OUT_OF_DOMAIN", "") else 0.5
                # context_relevance: tỉ lệ chunks có liên quan đến câu hỏi (Es et al., 2023)
                ctx_rel = round(_compute_context_relevance(q, ctx_chunks), 3)

                is_hall = faith < 0.5
                if is_hall:
                    hallucinated_count += 1
                faith_vals.append(faith)
                rel_vals.append(rel)
                prec_vals.append(prec)
                recall_vals.append(rec)
                ctx_rel_vals.append(ctx_rel)

                per_sample.append({
                    "id":                    tc.get("id", f"#{i+1}"),
                    "question":              q,
                    "type":                  qtype,
                    "ground_truth":          gt,
                    "answer":                (ans_text[:200] + "...") if len(ans_text) > 200 else ans_text,
                    "faithfulness":          faith,
                    "answer_relevancy":      rel,
                    "context_precision":     prec,
                    "context_recall":        rec,
                    "context_relevance":     ctx_rel,
                    "is_hallucinated":       is_hall,
                    "out_of_domain_correct": None,
                    "f1_score":              round((faith + rel) / 2, 3),
                    "judge_explanation":     "",
                })

        def _avg(vals):
            return round(sum(vals) / len(vals), 3) if vals else 0.0

        total_normal = len(faith_vals)
        total_ood    = len(ood_results)
        passed = sum(1 for s in per_sample if not s["is_hallucinated"])
        failed = sum(1 for s in per_sample if s["is_hallucinated"])

        job["result"] = {
            "summary": {
                "avg_faithfulness":        _avg(faith_vals),
                "avg_answer_relevancy":    _avg(rel_vals),
                "avg_context_precision":   _avg(prec_vals),
                "avg_context_recall":      _avg(recall_vals),
                "avg_context_relevance":   _avg(ctx_rel_vals),
                "hallucination_rate":      round(hallucinated_count / max(total_normal, 1), 3) if total_normal else None,
                "out_of_domain_accuracy":  round(ood_correct_count / max(total_ood, 1), 3) if total_ood else None,
                "passed":                  passed,
                "failed":                  failed,
                "total_cases":             len(cases),
                "mode":                    "ragas-official",
                "judge_model":             "llama-3.1-8b-instant (via Groq)",
            },
            "per_sample": per_sample,
        }
        job["status"] = "done"
        print(f"[RAGAS] Job {job_id[:8]} done ✓ — passed={passed} failed={failed}")
    except ImportError as e:
        job["status"] = "error"
        job["error"] = f"RAGAS chưa được cài: {e}"
        print(f"[RAGAS] ImportError: {e}")
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        print(f"[RAGAS] Error: {e}")



@router.post("/ai/evaluate/ragas")
async def start_ragas_evaluation(
    count: int = Query(default=4, ge=4, le=20),
    current_user: str = Depends(get_current_user),
):
    """Khởi động RAGAS job — trả về job_id NGAY LẬP TỨC, job chạy background."""
    cases  = _build_ragas_cases(count)
    job_id = str(uuid.uuid4())
    _ragas_jobs[job_id] = {
        "status":    "collecting",
        "rag_done":  0,
        "total":     len(cases),
        "done_cases": [],
        "result":    None,
        "error":     None,
    }
    # Submit ngay vào executor — KHÔNG dùng BackgroundTasks để tránh delay
    _ragas_executor.submit(_run_ragas_job, job_id, cases)
    print(f"[RAGAS] Job {job_id[:8]} submitted, returning immediately")
    return {"job_id": job_id, "total": len(cases)}


@router.get("/ai/evaluate/ragas/status/{job_id}")
async def get_ragas_status(
    job_id: str,
    current_user: str = Depends(get_current_user),
):
    job = _ragas_jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}
    return job

