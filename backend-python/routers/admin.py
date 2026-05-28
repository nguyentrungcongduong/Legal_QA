"""
routers/admin.py
================
Admin API cho việc quản lý văn bản pháp luật.

Endpoints:
  POST   /admin/upload-document          — Upload file + trigger background ingest
  GET    /admin/ingest-status/{job_id}   — Poll trạng thái job
  GET    /admin/documents                — Danh sách tài liệu đã ingest
  DELETE /admin/documents/{document_id}  — Xóa tài liệu (Qdrant + PostgreSQL)
  POST   /admin/re-ingest                — Re-ingest tài liệu đã có
  GET    /admin/stats                    — Thống kê tổng quan
  GET    /admin/users                    — Danh sách người dùng
  PATCH  /admin/users/{user_id}/role     — Thay đổi role người dùng
"""
from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import psycopg2
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from auth.jwt_verify import get_current_user, require_admin

load_dotenv()

router = APIRouter(prefix="/admin", tags=["admin"])

# ─── In-memory job store ──────────────────────────────────────────────────────
_jobs: dict[str, dict] = {}

# Executor riêng để chạy ingest đồng bộ mà không block event loop
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingest")

# ─── Config ───────────────────────────────────────────────────────────────────
ROOT_DIR  = Path(__file__).resolve().parent.parent
RAW_DIR   = ROOT_DIR / "data" / "raw"
PDF_STORE = ROOT_DIR / "data" / "pdf_store"
PG_CONN   = os.getenv("POSTGRES_URL", "postgresql://raguser:ragpass@localhost:5432/ragdb")


# ─── Models ───────────────────────────────────────────────────────────────────
class ReIngestRequest(BaseModel):
    document_id: str

class RoleUpdate(BaseModel):
    role: str


# ─── Law name formatter ──────────────────────────────────────────────────────
def _format_law_name(raw: str, document_code: str = "") -> str:
    """
    Chuẩn hoá tên văn bản pháp luật.
    VD: "168 2024 Nd-Cp 619502" → "Nghị định 168/2024/NĐ-CP"
        "52 2014 Qh13 238640"   → "Luật 52/2014/QH13"
        "91 2015 Qh13 296215"   → "Luật 91/2015/QH13"
    Nếu tên đã hợp lệ (có từ tiếng Việt) thì giữ nguyên.
    """
    import re

    if not raw:
        return raw

    # Đã có chữ tiếng Việt / ký tự hoa → tên đã đẹp, không đổi
    has_vn = bool(re.search(
        r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩ'
        r'òóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ'
        r'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨ'
        r'ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]', raw))
    has_prefix = bool(re.match(
        r'^(Nghị định|Thông tư|Quyết định|Luật|Bộ luật|Pháp lệnh|Hiến pháp)',
        raw, re.IGNORECASE))
    if has_vn or has_prefix:
        return raw

    # Pattern: "{số} {năm} {cơ_quan} {hash}" hoặc "{số}_{năm}_{cơ_quan}_{hash}"
    raw_norm = re.sub(r'[_\s]+', ' ', raw).strip()
    m = re.match(
        r'^(\d+)\s+(\d{4})\s+([A-Za-z0-9-]+?)(?:\s+\d+)?$',
        raw_norm
    )
    if not m:
        return raw  # không match → trả nguyên

    num, year, body = m.group(1), m.group(2), m.group(3)

    # Mapping cơ quan ban hành → (prefix VN, mã chuẩn)
    _BODY_MAP = {
        'nd-cp':    ('Nghị định',    'NĐ-CP'),
        'nd':       ('Nghị định',    'NĐ-CP'),
        'tt-bgtvt': ('Thông tư',     'TT-BGTVT'),
        'tt-bca':   ('Thông tư',     'TT-BCA'),
        'tt-blđtbxh': ('Thông tư',  'TT-BLĐTBXH'),
        'tt-btc':   ('Thông tư',     'TT-BTC'),
        'tt':       ('Thông tư',     'TT'),
        'qd-ttg':   ('Quyết định',   'QĐ-TTg'),
        'qd-bgtvt': ('Quyết định',   'QĐ-BGTVT'),
        'qd':       ('Quyết định',   'QĐ'),
    }
    body_key = body.lower()

    # Quốc hội: QH{khóa} → Luật số
    qh_m = re.match(r'qh(\d+)', body_key)
    if qh_m:
        qh_session = qh_m.group(1)
        return f"Luật {num}/{year}/QH{qh_session}"

    prefix, code = _BODY_MAP.get(body_key, (None, body.upper()))
    if prefix:
        return f"{prefix} {num}/{year}/{code}"

    # Fallback chung
    return f"{num}/{year}/{body.upper()}"


# ─── Background ingest runner ─────────────────────────────────────────────────
def _run_ingest_sync(job_id: str, file_path: str, metadata: dict) -> None:
    """Chạy đồng bộ trong ThreadPoolExecutor để tránh block event loop."""
    try:
        _jobs[job_id]["status"] = "processing"
        _jobs[job_id]["progress_pct"] = 30

        from ingestion.ingest import ingest_document

        _jobs[job_id]["progress_pct"] = 45
        total = ingest_document(file_path, metadata)

        _jobs[job_id].update({
            "status": "done",
            "total_chunks": total or 0,
            "progress_pct": 100,
        })
    except Exception as e:
        import traceback
        _jobs[job_id].update({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        })


async def _dispatch_ingest(job_id: str, file_path: str, metadata: dict) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _run_ingest_sync, job_id, file_path, metadata)


# ─── Upload & Ingest ──────────────────────────────────────────────────────────

@router.post("/upload-document")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    domain: str = Form(...),
    law_name: str = Form(...),
    document_code: str = Form(...),
    effective_date: str = Form(...),
    _user: dict = Depends(get_current_user),   # bất kỳ user đăng nhập đều upload được
):
    fname = file.filename or ""
    ext = fname.rsplit(".", 1)[-1].lower()
    if ext not in ("pdf", "docx", "doc"):
        raise HTTPException(400, detail="Chỉ hỗ trợ PDF, DOCX, DOC")

    save_dir = RAW_DIR / domain
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / fname

    content = await file.read()
    save_path.write_bytes(content)

    PDF_STORE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(save_path, PDF_STORE / fname)

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "filename": fname, "total_chunks": 0, "progress_pct": 10}

    metadata = {
        "document_id": str(uuid.uuid4()),
        "domain": domain,
        "law_name": _format_law_name(law_name, document_code),  # chuẩn hoá tên ngay lúc lưu
        "document_code": document_code,
        "law_type": "luat",
        "effective_date": effective_date,
        "expiry_date": None,
    }

    background_tasks.add_task(_dispatch_ingest, job_id, str(save_path), metadata)
    return {"job_id": job_id, "filename": fname}


@router.get("/ingest-status/{job_id}")
async def get_ingest_status(job_id: str, _user: dict = Depends(get_current_user)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, detail="Job không tồn tại")
    return job


# ─── Documents ────────────────────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(_user: dict = Depends(get_current_user)):
    try:
        conn = psycopg2.connect(PG_CONN)
        cur  = conn.cursor()
        cur.execute("""
            SELECT
                d.id, d.law_name, d.domain, d.document_code,
                d.effective_date, d.expiry_date,
                COALESCE(d.total_chunks, 0) as total_chunks
            FROM legal_documents d
            ORDER BY d.effective_date DESC NULLS LAST
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(500, detail=f"DB error: {e}")

    return [
        {
            "id":             str(r[0]),
            "law_name":       _format_law_name(r[1] or "", r[3] or ""),
            "domain":         r[2] or "unknown",
            "document_code":  r[3],
            "effective_date": str(r[4]) if r[4] else None,
            "expiry_date":    str(r[5]) if r[5] else None,
            "total_chunks":   r[6] or 0,
        }
        for r in rows
    ]


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    _admin: dict = Depends(require_admin),
):
    """Xóa tài liệu khỏi cả Qdrant và PostgreSQL."""
    try:
        conn = psycopg2.connect(PG_CONN)
        cur  = conn.cursor()

        cur.execute(
            "SELECT document_code, law_name, file_path FROM legal_documents WHERE id = %s",
            (document_id,)
        )
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            raise HTTPException(404, detail="Không tìm thấy văn bản")

        document_code, law_name, file_path = row

        # Xóa khỏi Qdrant
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            qdrant = QdrantClient(os.getenv("QDRANT_URL", "http://localhost:6333"))
            qdrant.delete(
                collection_name="legal_chunks",
                points_selector=Filter(must=[
                    FieldCondition(key="document_code", match=MatchValue(value=document_code))
                ])
            )
        except Exception as qe:
            print(f"[Admin] Qdrant delete warning: {qe}")

        # Xóa cascade trong PostgreSQL
        cur.execute("""
            DELETE FROM message_citations
            WHERE chunk_id IN (SELECT id FROM document_chunks WHERE document_id = %s)
        """, (document_id,))
        cur.execute("DELETE FROM document_chunks WHERE document_id = %s", (document_id,))
        cur.execute("DELETE FROM legal_documents WHERE id = %s", (document_id,))
        conn.commit()
        cur.close(); conn.close()

        # Xóa file vật lý nếu có
        if file_path and Path(file_path).exists():
            try:
                Path(file_path).unlink()
            except Exception:
                pass

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))

    return {"message": f"Đã xóa: {law_name}", "document_code": document_code}


@router.post("/re-ingest")
async def re_ingest(
    req: ReIngestRequest,
    background_tasks: BackgroundTasks,
    _admin: dict = Depends(require_admin),
):
    try:
        conn = psycopg2.connect(PG_CONN)
        cur  = conn.cursor()
        cur.execute(
            "SELECT file_path, law_name, document_code, law_type, effective_date, expiry_date, domain "
            "FROM legal_documents WHERE id = %s",
            (req.document_id,)
        )
        row = cur.fetchone()
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(500, detail=str(e))

    if not row:
        raise HTTPException(404, detail="Tài liệu không tìm thấy")

    file_path, law_name, doc_code, law_type, eff_date, exp_date, domain = row
    if not file_path or not Path(file_path).exists():
        raise HTTPException(400, detail=f"File không tồn tại: {file_path}")

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "total_chunks": 0, "progress_pct": 10}

    metadata = {
        "document_id":    req.document_id,
        "domain":         domain or "unknown",
        "law_name":       law_name,
        "document_code":  doc_code,
        "law_type":       law_type or "luat",
        "effective_date": str(eff_date) if eff_date else "2024-01-01",
        "expiry_date":    str(exp_date) if exp_date else None,
    }

    background_tasks.add_task(_dispatch_ingest, job_id, file_path, metadata)
    return {"job_id": job_id}


# ─── Statistics ───────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(_admin: dict = Depends(require_admin)):
    try:
        conn = psycopg2.connect(PG_CONN)
        cur  = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM legal_documents")
        total_docs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM document_chunks")
        total_chunks = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        # Đếm messages an toàn (bảng có thể khác nhau)
        total_messages = 0
        for tbl in ("chat_messages", "message"):
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                total_messages = cur.fetchone()[0]
                break
            except Exception:
                conn.rollback()

        # Phân bổ theo domain
        cur.execute("""
            SELECT d.domain,
                   COUNT(DISTINCT d.id) as doc_count,
                   COUNT(c.id) as chunk_count
            FROM legal_documents d
            LEFT JOIN document_chunks c ON c.document_id = d.id
            GROUP BY d.domain
            ORDER BY chunk_count DESC
        """)
        domain_stats = [
            {"domain": r[0], "doc_count": r[1], "chunk_count": r[2]}
            for r in cur.fetchall()
        ]

        cur.close(); conn.close()

    except Exception as e:
        raise HTTPException(500, detail=f"DB error: {e}")

    return {
        "overview": {
            "total_docs": total_docs,
            "total_chunks": total_chunks,
            "total_users": total_users,
            "total_messages": total_messages,
        },
        "domain_stats": domain_stats,
    }


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/users")
async def get_users(_admin: dict = Depends(require_admin)):
    try:
        conn = psycopg2.connect(PG_CONN)
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, email, role, created_at
            FROM users
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(500, detail=str(e))

    return [
        {
            "id":         str(r[0]),
            "email":      r[1],
            "role":       r[2] or "user",
            "created_at": str(r[3]),
        }
        for r in rows
    ]


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: RoleUpdate,
    _admin: dict = Depends(require_admin),
):
    if body.role not in ("admin", "user"):
        raise HTTPException(400, detail="Role phải là 'admin' hoặc 'user'")
    try:
        conn = psycopg2.connect(PG_CONN)
        cur  = conn.cursor()
        cur.execute("UPDATE users SET role = %s WHERE id = %s", (body.role, user_id))
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(500, detail=str(e))

    return {"message": f"Đã cập nhật role thành {body.role}"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: dict = Depends(require_admin),
):
    """Xóa người dùng. Không thể tự xóa chính mình."""
    if user_id == current_admin["user_id"]:
        raise HTTPException(400, detail="Không thể tự xóa tài khoản đang đăng nhập")
    try:
        conn = psycopg2.connect(PG_CONN)
        cur  = conn.cursor()
        cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            raise HTTPException(404, detail="Người dùng không tồn tại")
        email = row[0]
        # Xóa cascade: sessions + messages
        cur.execute("DELETE FROM chat_sessions WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cur.close(); conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    return {"message": f"Đã xóa người dùng: {email}"}
