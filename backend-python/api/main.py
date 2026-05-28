from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if not _env_file.exists():
        _env_file = Path(__file__).resolve().parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(dotenv_path=_env_file, override=False)
        print(f"[Env] Loaded .env from: {_env_file}")
    else:
        print("[Env] WARNING: .env not found — API keys may be missing!")
except ImportError:
    pass

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import threading
from pathlib import Path
from urllib.parse import quote

from datetime import datetime, timezone

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from retriever.hybrid_retriever import get_retriever
from retriever.conflict_detector import ConflictDetector
from generator.generator import Generator
from guard.query_rewriter import QueryRewriter
from guard.domain_router import DomainRouter
from auth.jwt_verify import get_current_user

from routers.compare import router as compare_router
from routers.evaluate import router as eval_router
from routers.admin import router as admin_router
from ingestion.file_watcher import start_watcher

app = FastAPI(title="Legal QA API", version="0.2.0")
app.include_router(compare_router)
app.include_router(eval_router)
app.include_router(admin_router)


@app.on_event("startup")
async def startup_event():
    """Khởi động file watcher trong background thread khi app start."""
    watch_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    watch_dir.mkdir(parents=True, exist_ok=True)
    watcher_thread = threading.Thread(
        target=start_watcher,
        args=(str(watch_dir),),
        daemon=True,
    )
    watcher_thread.start()
    print(f"[App] File watcher khoi dong -> dang theo doi: {watch_dir}")

retriever        = get_retriever()
conflict_detector = ConflictDetector()
generator        = Generator()
query_rewriter   = QueryRewriter()
domain_router    = DomainRouter()

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


class ChatMessage(BaseModel):
    role: str           # "user" | "assistant"
    content: str
    domain: str | None = None   # domain của lượt trước (gữi từ frontend để enable follow-up detection)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1,
                          description="Natural language legal question")
    top_k: int = Field(5, ge=1, le=20)
    model_preference: str = Field(
        default="auto",
        description="LLM ưu tiên: auto | groq | gemini | openai | template"
    )
    prev_domain: str | None = Field(
        default=None,
        description="Domain của lượt chat trước để detect follow-up (gữi bởi frontend)"
    )
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
    model_used: str | None = None            # groq | gemini | openai | template


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
    # Lay prev_domain tu QueryRequest de enable follow-up detection
    # Frontend can gui kem detected_domain cua luot truoc trong chat_history
    prev_domain: str | None = None
    if payload.chat_history:
        # Tim domain cua assistant message gan nhat trong chat_history extension
        # Frontend truyen them field domain vao history neu co
        for m in reversed(payload.chat_history):
            if m.role == "assistant" and hasattr(m, "domain") and m.domain:
                prev_domain = m.domain
                break

    # Neu frontend khong truyen domain, thu detect tu assistant message cuoi
    # bang cach kiem tra xem co detected_domain nao trong payload khong
    if not prev_domain and hasattr(payload, "prev_domain") and payload.prev_domain:
        prev_domain = payload.prev_domain

    domain = domain_router.classify(payload.question, prev_domain=prev_domain)
    domain_info = domain_router.get_info(domain)
    print(f"[DomainRouter] '{payload.question[:50]}' → domain='{domain}' (prev='{prev_domain}')")

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
    # FIXED: retriever.py đã đồng nhất về BAAI/bge-m3 với ingest.py
    # → vector space nhất quán → có thể dùng threshold cao hơn
    SIMILARITY_THRESHOLD = 0.45
    top_score = (results[0].get("dense_score") or 0.0) if results else 0.0

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
        domain=domain,                              # <- dynamic persona
        model_preference=payload.model_preference,  # <- user-selected LLM
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
        model_used=gen_result.get("model_used"),
    )


