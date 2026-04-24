import os
import re
import sys
import uuid

import docx
import fitz  # PyMuPDF
import mammoth
import psycopg2
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

load_dotenv(
    os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
    override=True,
)

# ============================================================
# CONFIG
# ============================================================
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "legal_chunks")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
PG_CONN = os.getenv(
    "POSTGRES_URL",
    "postgresql://raguser:ragpass@localhost:5432/ragdb",
)

qdrant = QdrantClient(QDRANT_URL, timeout=120.0)
embedder = SentenceTransformer(EMBEDDING_MODEL)


def _resolve_input_path(file_path: str) -> str:
    """Đường dẫn tương đối tính từ thư mục backend-python (không phụ thuộc cwd)."""
    expanded = os.path.expanduser(file_path)
    if os.path.isabs(expanded):
        return os.path.normpath(expanded)
    root = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    )
    return os.path.normpath(os.path.join(root, expanded))


# Word 97–2003 / OLE compound (đuôi .docx giả)
_OLE_DOC_MAGIC = b"\xd0\xcf\x11\xe0"


def _sniff_document_format(path: str) -> str | None:
    """Nhận diện pdf / docx (ZIP) / doc (OLE) bằng magic; None nếu không khớp."""
    with open(path, "rb") as f:
        head = f.read(8)
    if len(head) >= 4 and head[:4] == b"%PDF":
        return "pdf"
    if len(head) >= 2 and head[:2] == b"PK":
        return "docx"
    if len(head) >= 4 and head[:4] == _OLE_DOC_MAGIC:
        return "doc"
    return None


# ============================================================
# STEP 1: ĐỌC FILE (PDF / DOCX / DOC) + CLEAN
# ============================================================
def extract_text_from_pdf_with_pages(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc, 1):
        text = page.get_text("text")
        text = clean_text(text)
        pages.append({
            "text": text,
            "page_number": page_num
        })
    return pages


def _normalize_for_match(text: str) -> str:
    return " ".join((text or "").lower().split())





def clean_text(text: str) -> str:
    # Xóa watermark, header/footer lặp lại
    text = re.sub(r"Trang \d+ / \d+", "", text)
    text = re.sub(r"©.*?\n", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # PDF/DOC: chữ thường + chữ hoa dính → chèn space ("Nghịđịnh" nếu có Định hoa; tổng quát cho từ ghép)
    _vn_lower = r"a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    _vn_upper = r"A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ"
    text = re.sub(rf"([{_vn_lower}])([{_vn_upper}])", r"\1 \2", text)

    # Chữ và số dính: "khoản1", "xửphạt" không khớp; "mức5" → "mức 5"
    text = re.sub(rf"([{_vn_lower}])(\d)", r"\1 \2", text)
    text = re.sub(rf"(\d)([{_vn_lower}])", r"\1 \2", text)

    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_text_from_file(file_path: str) -> str:
    path = _resolve_input_path(file_path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    fmt = _sniff_document_format(path)
    if fmt is None:
        _, ext = os.path.splitext(path)
        fmt = ext.lstrip(".").lower()
    if not fmt:
        raise ValueError("Không xác định được định dạng file")

    if fmt == "pdf":
        raise ValueError("Use extract_text_from_pdf_with_pages for PDF")
    if fmt == "docx":
        return extract_text_from_docx(path)
    if fmt == "doc":
        return extract_text_from_doc(path)
    raise ValueError(f"Không hỗ trợ định dạng: {fmt}")


def extract_text_from_docx(file_path: str) -> str:
    doc = docx.Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)
    return clean_text(text)


def extract_text_from_doc(file_path: str) -> str:
    # .docx là ZIP (bắt đầu PK); mammoth đọc được. .doc nhị phân (OLE) không phải ZIP —
    # mammoth sẽ lỗi; khi đó dùng Word qua pywin32 nếu có.
    with open(file_path, "rb") as f:
        sig = f.read(4)
    if sig[:2] == b"PK":
        with open(file_path, "rb") as f:
            result = mammoth.extract_raw_text(f)
        return clean_text(result.value)
    return _extract_text_from_legacy_doc_binary(file_path)


def _extract_text_from_legacy_doc_binary(file_path: str) -> str:
    try:
        import win32com.client
    except ImportError as e:
        raise ValueError(
            "File .doc nhị phân cần Microsoft Word + pywin32, hoặc xuất lại .docx/.pdf."
        ) from e

    path = os.path.abspath(file_path)
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(path)
        text = doc.Content.Text
        doc.Close(False)
    finally:
        word.Quit()
    return clean_text(text)


# ============================================================
# STEP 2: SMART CHUNKING — tách theo Điều/Khoản
# ============================================================
def smart_chunk_with_pages(pages: list[dict], document_metadata: dict) -> list[dict]:
    chunks = []
    MIN_CHUNK_LENGTH = 50

    # 1. Build full text and page offsets
    full_text = ""
    page_offsets = [] # list of (start_idx, end_idx, page_number)
    current_idx = 0
    
    for page_data in pages:
        text = page_data["text"]
        page_num = page_data["page_number"]
        start_idx = current_idx
        full_text += text + "\n\n"
        current_idx = len(full_text)
        page_offsets.append((start_idx, current_idx, page_num))
        
    def get_page_for_offset(offset: int) -> int:
        for start, end, p_num in page_offsets:
            if start <= offset < end:
                return p_num
        # Fallback to last page if out of bounds somehow
        return page_offsets[-1][2] if page_offsets else 1

    # Regex nhận diện bắt đầu Điều
    dieu_pattern = re.compile(
        r"(Điều\s+(\d+)\s*[.\:]\s*[^\n]+(?:\n(?!Điều\s+\d+).*)*)",
        re.MULTILINE,
    )

    for match in dieu_pattern.finditer(full_text):
        dieu_text = match.group(1).strip()
        dieu_number = match.group(2)
        dieu_title_line = dieu_text.split("\n")[0]
        
        # Calculate offset of this Điều to map to the correct page
        dieu_offset = match.start(1)
        dieu_page_number = get_page_for_offset(dieu_offset)

        # Tách tiếp theo Khoản bên trong Điều
        khoan_pattern = re.compile(r"(\d+\.\s.+?)(?=\n\d+\.\s|\Z)", re.DOTALL)
        khoan_matches = list(khoan_pattern.finditer(dieu_text))

        if khoan_matches:
            for km in khoan_matches:
                khoan_text = km.group(1).strip()
                if len(khoan_text) < MIN_CHUNK_LENGTH:
                    continue
                khoan_number = khoan_text.split(".")[0]
                
                # Calculate offset of Khoan relative to full_text
                khoan_offset = dieu_offset + km.start(1)
                k_page_number = get_page_for_offset(khoan_offset)

                chunks.append(
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "content": khoan_text,
                        "article": f"Điều {dieu_number}",
                        "article_title": dieu_title_line,
                        "clause": f"Khoản {khoan_number}",
                        "full_article_text": dieu_text,
                        "page_number": k_page_number,
                        **document_metadata,
                    }
                )
        else:
            if len(dieu_text) < MIN_CHUNK_LENGTH:
                continue
            chunks.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "content": dieu_text,
                    "article": f"Điều {dieu_number}",
                    "article_title": dieu_title_line,
                    "clause": None,
                    "full_article_text": dieu_text,
                    "page_number": dieu_page_number,
                    **document_metadata,
                }
            )

    return chunks


# ============================================================
# STEP 3: EMBED + LƯU VÀO QDRANT VÀ POSTGRES
# ============================================================
def ingest_document(file_path: str, document_metadata: dict):
    resolved = _resolve_input_path(file_path)
    print(f"[1/4] Đọc file: {resolved}")
    fmt = _sniff_document_format(resolved) or os.path.splitext(resolved)[
        1].lstrip(".").lower()
    pages_dict = []
    if fmt == "pdf":
        pages_dict = extract_text_from_pdf_with_pages(resolved)
    else:
        text = extract_text_from_file(file_path)
        pages_dict = [{"text": text, "page_number": 1}]

    print("[2/4] Smart chunking with pages tracking...")
    chunks = smart_chunk_with_pages(pages_dict, document_metadata)
    print(f"      → {len(chunks)} chunks")

    print(f"[3/4] Embedding {len(chunks)} chunks...")
    contents = [c["content"] for c in chunks]
    vectors = embedder.encode(contents, batch_size=32, show_progress_bar=True)

    print("[4/4] Lưu vào Qdrant + PostgreSQL...")
    _save_to_qdrant(chunks, vectors, resolved)
    _save_to_postgres(chunks, document_metadata, resolved)

    print(f"Done! Ingested {len(chunks)} chunks.")


def _save_to_qdrant(chunks: list, vectors, source_file_path: str):
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

    points = []
    source_file = os.path.basename(source_file_path)
    for chunk, vector in zip(chunks, vectors):
        points.append(
            PointStruct(
                id=chunk["chunk_id"],
                vector=vector.tolist(),
                payload={
                    "content": chunk["content"],
                    "article": chunk["article"],
                    "article_title": chunk["article_title"],
                    "clause": chunk["clause"],
                    "law_name": chunk["law_name"],
                    "document_code": chunk["document_code"],
                    "law_type": chunk["law_type"],
                    "effective_date": chunk["effective_date"],
                    "expiry_date": chunk.get("expiry_date"),
                    "page_number": chunk.get("page_number"),
                    "source_file": source_file,
                    "document_id": chunk["document_id"],
                },
            )
        )

    for i in range(0, len(points), 100):
        qdrant.upsert(collection_name=COLLECTION_NAME,
                      points=points[i: i + 100])


def _save_to_postgres(chunks: list, doc_meta: dict, source_file_path: str):
    conn = psycopg2.connect(PG_CONN)
    cur = conn.cursor()
    n = len(chunks)
    cur.execute(
        """
        INSERT INTO legal_documents
            (id, law_name, document_code, law_type, effective_date, expiry_date, file_path, total_chunks)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            law_name = EXCLUDED.law_name,
            document_code = EXCLUDED.document_code,
            law_type = EXCLUDED.law_type,
            effective_date = EXCLUDED.effective_date,
            expiry_date = EXCLUDED.expiry_date,
            file_path = EXCLUDED.file_path,
            total_chunks = EXCLUDED.total_chunks
        """,
        (
            doc_meta["document_id"],
            doc_meta["law_name"],
            doc_meta["document_code"],
            doc_meta.get("law_type"),
            doc_meta["effective_date"],
            doc_meta.get("expiry_date"),
            source_file_path,
            n,
        ),
    )
    for idx, chunk in enumerate(chunks):
        cur.execute(
            """
            INSERT INTO document_chunks
                (id, document_id, qdrant_id, article, clause, content, page_number, chunk_index)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                chunk["chunk_id"],
                doc_meta["document_id"],
                chunk["chunk_id"],
                chunk["article"],
                chunk["clause"],
                chunk["content"],
                chunk.get("page_number"),
                idx,
            ),
        )
    conn.commit()
    cur.close()
    conn.close()


# ============================================================
# CHẠY
# ============================================================
if __name__ == "__main__":
    # Luôn: cd backend-python && .\.venv\Scripts\Activate.ps1  (thấy (.venv) rồi mới chạy)
    # Ingest từng file: sửa FILE_PATH + DOCUMENT_METADATA, chạy một lần, rồi đổi sang file kế.

    # --- Lần 1 (xong thì comment và bật block Luật 2008) ---
    # --- Cấu hình cho file Nghị định 100/2019 ---
    FILE_PATH = "data/pdf_store/nd_100_2019.pdf"
    DOCUMENT_METADATA = {
        "law_name": "Nghị định 100/2019/NĐ-CP",
        "document_code": "100/2019/NĐ-CP",
        "law_type": "nghi_dinh",
        "effective_date": "2020-01-01",
        "expiry_date": None,
    }

    # --- Lần 2: bỏ comment block dưới, comment block nd_123 phía trên ---
    # FILE_PATH = "data/raw/luat_gtdb_2008.docx"
    # DOCUMENT_METADATA = {
    #     "law_name": "Luật Giao thông đường bộ 2008",
    #     "document_code": "23/2008/QH12",
    #     "law_type": "luat",
    #     "effective_date": "2009-07-01",
    #     "expiry_date": None,
    # }luat_gtdb_2008

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except OSError:
            pass

    meta = {**DOCUMENT_METADATA, "document_id": str(uuid.uuid4())}
    ingest_document(FILE_PATH, meta)
