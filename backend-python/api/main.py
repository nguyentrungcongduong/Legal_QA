from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field

from retriever.hybrid_retriever import HybridRetriever

app = FastAPI(title="Legal QA API", version="0.1.0")
retriever = HybridRetriever()


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Natural language legal question")
    top_k: int = Field(5, ge=1, le=20)


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


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]


class CompareRequest(BaseModel):
    question_a: str = Field(..., min_length=3)
    question_b: str = Field(..., min_length=3)
    top_k: int = Field(5, ge=1, le=20)


class EvaluationCase(BaseModel):
    question: str = Field(..., min_length=3)
    expected_keywords: list[str] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    cases: list[EvaluationCase] = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)


def _citations_from_results(results: list[dict]) -> list[Citation]:
    citations: list[Citation] = []
    for item in results:
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
            )
        )
    return citations


def _build_answer(question: str, citations: list[Citation]) -> str:
    if not citations:
        return f"Chua tim thay can cu phu hop cho cau hoi: '{question}'."
    top = citations[0]
    snippet = (top.content or "").strip().replace("\n", " ")
    snippet = " ".join(snippet.split())[:280]
    return (
        f"Theo {top.law_name or 'van ban phap luat'}"
        f" ({top.article or 'khong ro dieu'}"
        f"{', ' + top.clause if top.clause else ''}), "
        f"noi dung lien quan la: {snippet}."
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(tz=timezone.utc).isoformat()}


@app.post("/ai/query", response_model=QueryResponse)
def ai_query(payload: QueryRequest) -> QueryResponse:
    results = retriever.search(payload.question, top_k=payload.top_k)
    citations = _citations_from_results(results)
    return QueryResponse(answer=_build_answer(payload.question, citations), citations=citations)


@app.post("/ai/compare")
def ai_compare(payload: CompareRequest) -> dict:
    a_results = retriever.search(payload.question_a, top_k=payload.top_k)
    b_results = retriever.search(payload.question_b, top_k=payload.top_k)

    a_citations = _citations_from_results(a_results)
    b_citations = _citations_from_results(b_results)

    overlap = sorted(
        {
            f"{c.law_name}|{c.article}|{c.clause}"
            for c in a_citations
            if f"{c.law_name}|{c.article}|{c.clause}"
            in {f"{x.law_name}|{x.article}|{x.clause}" for x in b_citations}
        }
    )
    return {
        "query_a": {
            "question": payload.question_a,
            "answer": _build_answer(payload.question_a, a_citations),
            "citations": a_citations,
        },
        "query_b": {
            "question": payload.question_b,
            "answer": _build_answer(payload.question_b, b_citations),
            "citations": b_citations,
        },
        "overlap_count": len(overlap),
        "overlap_keys": overlap,
    }


@app.post("/ai/evaluate")
def ai_evaluate(payload: EvaluateRequest) -> dict:
    details: list[dict] = []
    passed = 0
    for case in payload.cases:
        results = retriever.search(case.question, top_k=payload.top_k)
        citations = _citations_from_results(results)
        answer = _build_answer(case.question, citations).lower()
        keywords = [k.lower() for k in case.expected_keywords]
        matched = [k for k in keywords if k in answer]
        ok = len(matched) == len(keywords) if keywords else bool(citations)
        if ok:
            passed += 1
        details.append(
            {
                "question": case.question,
                "expected_keywords": case.expected_keywords,
                "matched_keywords": matched,
                "passed": ok,
                "answer": answer,
                "top_citation": citations[0].model_dump() if citations else None,
            }
        )
    total = len(payload.cases)
    return {
        "total": total,
        "passed": passed,
        "score": (passed / total) if total else 0.0,
        "details": details,
    }
