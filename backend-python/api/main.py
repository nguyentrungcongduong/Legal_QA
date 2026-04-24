from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from datetime import datetime, timezone

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from retriever.hybrid_retriever import HybridRetriever
from retriever.conflict_detector import ConflictDetector
from generator.generator import Generator
from guard.query_rewriter import QueryRewriter
from guard.domain_router import DomainRouter
from auth.jwt_verify import get_current_user

from routers.compare import router as compare_router
from routers.evaluate import router as eval_router

app = FastAPI(title="Legal QA API", version="0.2.0")
app.include_router(compare_router)
app.include_router(eval_router)

retriever        = HybridRetriever()
conflict_detector = ConflictDetector()
generator        = Generator()
query_rewriter   = QueryRewriter()
domain_router    = DomainRouter()

# Dev CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_PDF_DIR = Path(__file__).resolve().parent.parent / "data" / "pdf_store"
if not _PDF_DIR.exists():
    _PDF_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/pdf-files", StaticFiles(directory=str(_PDF_DIR)), name="pdfs")


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str           # "user" | "assistant"
    content: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1,
                          description="Natural language legal question")
    top_k: int = Field(5, ge=1, le=20)
    chat_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Lich su hoi thoai (toi da 6 messages gan nhat)"
    )


class Citation(BaseModel):
    chunk_id: str
    law_name: str | None = None
    article: str | None = None
    clause: str | None = None
    document_code: str | None = None
    law_type: str | None = None
    content: str | None = None
    effective_date: str | None = None
    expiry_date: str | None = None
    dense_score: float | None = None
    sparse_score: float | None = None
    rrf_score: float | None = None
    page_number: int | None = None
    pdf_url: str | None = None
    file_name: str | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    conflicts: list[dict] = Field(default_factory=list)
    has_conflict: bool = False
    rewritten_query: str | None = None
    detected_domain: str | None = None       # giao_thong | dat_dai | ...
    domain_label: str | None = None          # "Luật Giao thông" (hiển thị UI)
    domain_emoji: str | None = None          # emoji cho UI


class EvaluationCase(BaseModel):
    question: str = Field(..., min_length=3)
    expected_keywords: list[str] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    cases: list[EvaluationCase] = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _citations_from_results(results: list[dict]) -> list[Citation]:
    citations: list[Citation] = []
    for item in results:
        source_file = item.get("source_file")
        file_path   = item.get("file_path")
        file_name   = item.get("file_name")
        page_number = item.get("page_number")

        pdf_url = None
        if source_file:
            pdf_url = f"/pdf-files/{quote(str(source_file))}"
        elif file_name:
            pdf_url = f"/pdf-files/{quote(str(file_name))}"
        elif file_path and str(file_path).lower().endswith(".pdf"):
            pdf_url = f"/pdf-files/{quote(os.path.basename(str(file_path)))}"

        citations.append(
            Citation(
                chunk_id=str(item.get("chunk_id", "")),
                law_name=item.get("law_name"),
                article=item.get("article"),
                clause=item.get("clause"),
                document_code=item.get("document_code"),
                law_type=item.get("law_type"),
                content=item.get("content"),
                effective_date=item.get("effective_date"),
                expiry_date=item.get("expiry_date"),
                dense_score=item.get("dense_score"),
                sparse_score=item.get("sparse_score"),
                rrf_score=item.get("rrf_score"),
                page_number=page_number,
                pdf_url=pdf_url,
                file_name=file_name,
            )
        )
    return citations


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(tz=timezone.utc).isoformat()}


@app.post("/ai/query", response_model=QueryResponse)
def ai_query(
    payload: QueryRequest,
    current_user: str = Depends(get_current_user),
) -> QueryResponse:
    print(f"[query] user={current_user} q='{payload.question[:60]}'")

    history = [{"role": m.role, "content": m.content} for m in payload.chat_history]

    # ── LAYER 1: Small-talk guard & Query Rewrite ──────────────────────────────
    rewritten = query_rewriter.rewrite(payload.question, history)

    # ── LAYER 2: Domain Classification (Semantic Router) ──────────────────────
    # Chay song song voi rewrite — classify tren cau hoi GÔC (nhay cam hon)
    domain = domain_router.classify(payload.question)
    domain_info = domain_router.get_info(domain)
    print(f"[DomainRouter] '{payload.question[:50]}' → domain='{domain}'")

    # Hard-stop cho small_talk — khong can chay RAG
    if domain == "small_talk":
        greet = (
            "Xin chào! Tôi là trợ lý pháp luật Việt Nam.\n"
            "Tôi có thể tư vấn về:\n"
            "🚦 Luật Giao thông · 🏡 Luật Đất đai · "
            "👷 Luật Lao động · ⚖️ Luật Dân sự · 🔒 Luật Hình sự\n\n"
            "Hôm nay bạn cần tư vấn về lĩnh vực nào?"
        )
        return QueryResponse(
            answer=greet,
            citations=[], conflicts=[], has_conflict=False,
            rewritten_query=None,
            detected_domain="small_talk",
            domain_label="Xã giao",
            domain_emoji="👋",
        )

    # ── LAYER 3: Retrieve với domain filter ────────────────────────────────────
    results = retriever.search(rewritten, top_k=payload.top_k, domain=domain)

    # ── LAYER 3b: Similarity Threshold Guard ───────────────────────────────────
    SIMILARITY_THRESHOLD = 0.35
    top_score = results[0].get("dense_score", 0) if results else 0

    if not results or top_score < SIMILARITY_THRESHOLD:
        print(f"[IntentGuard] score={top_score:.3f} < {SIMILARITY_THRESHOLD} — OOD")
        polite = (
            f"Câu hỏi này nằm ngoài phạm vi tư vấn hiện tại của tôi "
            f"trong lĩnh vực {domain_info.label_vi}. "
            "Bạn có thể thử đặt câu hỏi cụ thể hơn hoặc hỏi về lĩnh vực khác như: "
            "Luật Giao thông, Luật Đất đai, Luật Lao động."
        )
        return QueryResponse(
            answer=polite,
            citations=[], conflicts=[], has_conflict=False,
            rewritten_query=None,
            detected_domain=domain,
            domain_label=domain_info.label_vi,
            domain_emoji=domain_info.emoji,
        )

    # ── LAYER 4: Conflict detection ────────────────────────────────────────────
    conflict_result  = conflict_detector.detect_and_resolve(results)
    resolved_chunks  = conflict_result["resolved_chunks"]
    conflicts        = conflict_result["conflicts"]
    has_conflict     = conflict_result["has_conflict"]

    # ── LAYER 5: Generate với Dynamic Persona ──────────────────────────────────
    gen_result = generator.generate(
        query=rewritten,
        chunks=resolved_chunks,
        conflicts=conflicts,
        chat_history=history,
        domain=domain,              # <- dynamic persona
    )

    raw_citations = gen_result.get("citations", [])
    typed_citations = [Citation(**c) for c in raw_citations]

    return QueryResponse(
        answer=gen_result["answer"],
        citations=typed_citations,
        conflicts=conflicts,
        has_conflict=has_conflict,
        rewritten_query=rewritten if rewritten != payload.question else None,
        detected_domain=domain,
        domain_label=domain_info.label_vi,
        domain_emoji=domain_info.emoji,
    )



@app.post("/ai/evaluate")
def ai_evaluate(payload: EvaluateRequest) -> dict:
    details: list[dict] = []
    passed = 0
    for case in payload.cases:
        results   = retriever.search(case.question, top_k=payload.top_k)
        citations = _citations_from_results(results)

        # Dung generator de build answer chuan hon
        gen       = generator.generate(query=case.question, chunks=results)
        answer    = gen["answer"].lower()

        keywords  = [k.lower() for k in case.expected_keywords]
        matched   = [k for k in keywords if k in answer]
        ok        = len(matched) == len(keywords) if keywords else bool(citations)
        if ok:
            passed += 1
        details.append({
            "question":          case.question,
            "expected_keywords": case.expected_keywords,
            "matched_keywords":  matched,
            "passed":            ok,
            "answer":            answer,
            "top_citation":      citations[0].model_dump() if citations else None,
        })
    total = len(payload.cases)
    return {
        "total":   total,
        "passed":  passed,
        "score":   (passed / total) if total else 0.0,
        "details": details,
    }
