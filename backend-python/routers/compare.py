"""
routers/compare.py  —  So sanh 3 mo hinh song song, tat ca FREE 100%:

  COT 1 : Legal RAG          — du lieu luat that + Hybrid Retriever
  COT 2 : Llama 3.3 70B     — Meta, via Groq,  KHONG co RAG
  COT 3 : Llama 4 Scout 17B — Meta (the he moi nhat), via Groq, KHONG co RAG

Demo pitch:
  "Cung la model cua Meta nhung khi duoc cap du lieu luat (RAG)
   thi do chinh xac tang vuot bac so voi vanilla."
"""
import asyncio
import os
from fastapi import APIRouter, Depends
from dotenv import load_dotenv
from auth.jwt_verify import get_current_user
from retriever.hybrid_retriever import HybridRetriever
from retriever.conflict_detector import ConflictDetector
from generator.generator import Generator

load_dotenv()

router = APIRouter()
retriever = HybridRetriever()
conflict_detector = ConflictDetector()
generator = Generator()

SYSTEM_PROMPT = (
    "Ban la tro ly phap luat Viet Nam. "
    "Hay tra loi cau hoi dua tren kien thuc cua ban. "
    "Tra loi ngan gon, ro rang bang tieng Viet."
)


# ──────────────────────────────────────────────
# Helper: goi bat ky model nao tren Groq
# ──────────────────────────────────────────────
async def _groq(model: str, messages: list) -> str:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def _sync():
        return client.chat.completions.create(
            model=model, messages=messages,
            temperature=0.7, max_tokens=600,
        )

    resp = await asyncio.to_thread(_sync)
    return resp.choices[0].message.content


# ──────────────────────────────────────────────
# COT 2 : Llama 3.3 70B Vanilla  (KHONG RAG)
# ──────────────────────────────────────────────
async def call_vanilla_llama(query: str) -> dict:
    try:
        answer = await _groq(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": query},
            ],
        )
        return {"answer": answer, "citations": [], "has_citations": False,
                "model": "llama-3.3-70b-vanilla", "error": None}
    except Exception as e:
        return {"answer": None, "citations": [], "has_citations": False,
                "model": "llama-3.3-70b-vanilla", "error": str(e)}


# ──────────────────────────────────────────────
# COT 3 : Llama 4 Scout 17B Vanilla  (KHONG RAG)
# Model the he moi nhat cua Meta — rat manh nhung thieu du lieu luat VN
# ──────────────────────────────────────────────
async def call_vanilla_gemini(query: str) -> dict:
    try:
        answer = await _groq(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "user",
                 "content": f"{SYSTEM_PROMPT}\n\nCau hoi: {query}"},
            ],
        )
        return {"answer": answer, "citations": [], "has_citations": False,
                "model": "llama4-scout-vanilla", "error": None}
    except Exception as e:
        return {"answer": None, "citations": [], "has_citations": False,
                "model": "llama4-scout-vanilla", "error": str(e)}


# ──────────────────────────────────────────────
# COT 1 : Legal RAG  (du lieu luat that)
# ──────────────────────────────────────────────
async def run_rag_pipeline(query: str) -> dict:
    try:
        chunks = retriever.search(query, top_k=20)
        result  = conflict_detector.detect_and_resolve(chunks)
        resolved = result["resolved_chunks"][:5]

        resp = generator.generate(
            query=query, chunks=resolved, conflicts=result["conflicts"]
        )
        return {
            **resp,
            "has_citations": True,
            "model": "legal-rag",
            "conflicts": result["conflicts"],
            "error": None,
        }
    except Exception as e:
        return {"answer": None, "citations": [], "has_citations": False,
                "model": "legal-rag", "conflicts": [], "error": str(e)}


# ──────────────────────────────────────────────
# Endpoint chinh
# ──────────────────────────────────────────────
@router.post("/ai/compare")
async def compare_models(
    request: dict,
    current_user: str = Depends(get_current_user),
):
    query = request.get("query", "")

    rag_result, llama_result, llama4_result = await asyncio.gather(
        run_rag_pipeline(query),
        call_vanilla_llama(query),
        call_vanilla_gemini(query),
    )

    return {
        "query":          query,
        "rag":            rag_result,
        "vanilla_gpt":    llama_result,   # key giu nguyen -> khong break frontend
        "vanilla_gemini": llama4_result,  # key giu nguyen -> khong break frontend
    }
