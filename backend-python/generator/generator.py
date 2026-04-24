"""
generator/generator.py
Sinh cau tra loi tu RAG chunks.
- Khi co Groq API key: dung Llama 3.3 de tao cau tra loi chat luong cao
- Fallback: template-based (khong can API)
"""
import os


_BASE_SYSTEM_TEMPLATE = """Bạn là {persona}.
Nhiệm vụ: Dựa trên CÁC VĂN BẢN PHÁP LUẬT được cung cấp, tư vấn cho khách hàng một cách chính xác, rõ ràng, có trích dẫn.

Quy tắc QUAN TRỌNG nhất:
1. CHỈ dùng thông tin có trong văn bản pháp luật được cung cấp — TUYỆT ĐỐI KHÔNG tự bịa thêm
2. Nếu thông tin cung cấp KHÔNG liên quan đến câu hỏi → Trả lời: "Tôi không tìm thấy quy định cụ thể cho vấn đề này trong hệ thống. Vui lòng thử lại với câu hỏi pháp lý rõ ràng hơn."
3. Nếu người dùng chào hỏi hoặc hỏi câu NGOÀI PHẠM VI → Chỉ trả lời lịch sự ngắn gọn, TUYỆT ĐỐI KHÔNG lôi văn bản pháp lý vào
4. Nếu điền số tiền, thời gian, mức phạt phải chính xác theo văn bản
5. Trích dẫn cụ thể: tên văn bản, điều, khoản theo định dạng [số]
6. Viết bằng tiếng Việt, văn phong chuyên nghiệp

Kiểm tra trước khi trả lời: "Thông tin pháp luật được cung cấp có THẬT SỰ trả lời cho câu hỏi này không?" Nếu KHÔNG → Nói rõ không biết, đừng bịa."""


def _build_system_prompt(domain: str | None = None) -> str:
    """Tao system prompt voi Dynamic Persona theo domain."""
    from guard.domain_router import DOMAINS
    info = DOMAINS.get(domain or "giao_thong", DOMAINS["giao_thong"])
    persona = info.persona or (
        "chuyên gia tư vấn pháp luật Việt Nam đa lĩnh vực"
    )
    return _BASE_SYSTEM_TEMPLATE.format(persona=persona)


class Generator:
    """
    Sinh cau tra loi phap luat tu danh sach chunks da retrieve.
    Ho tro Dynamic Persona theo domain.
    """

    def __init__(self):
        self._groq_key = os.getenv("GROQ_API_KEY")

    def generate(
        self,
        query: str,
        chunks: list[dict],
        conflicts: list = None,
        chat_history: list[dict] = None,
        domain: str | None = None,   # <- moi: dynamic persona
    ) -> dict:
        """
        Args:
            query:        Cau hoi da duoc rewrite
            chunks:       Chunks tu retriever
            conflicts:    Xung dot phap ly
            chat_history: Lich su hoi thoai
            domain:       Linh vuc phap luat (giao_thong/dat_dai/...)

        Returns:
            dict: {answer, citations}
        """
        citations = self._build_citations(chunks)

        if not chunks:
            return {
                "answer": f"Không tìm thấy căn cứ pháp lý phù hợp cho câu hỏi: '{query}'.",
                "citations": [],
            }

        # Thu dung Groq neu co key
        if self._groq_key:
            try:
                answer = self._generate_with_groq(
                    query, chunks, conflicts, chat_history, domain=domain
                )
                return {"answer": answer, "citations": citations}
            except Exception as e:
                print(f"[Generator] Groq error: {e} — fallback to template")

        # Fallback: template-based
        answer = self._generate_template(query, chunks, conflicts)
        return {"answer": answer, "citations": citations}

    # ─────────────────────────────────────────────────────
    # Groq-based generation (chat luong cao)
    # ─────────────────────────────────────────────────────
    def _generate_with_groq(
        self,
        query: str,
        chunks: list[dict],
        conflicts: list = None,
        chat_history: list[dict] = None,
        domain: str | None = None,       # <- dynamic persona
    ) -> str:
        from groq import Groq
        client = Groq(api_key=self._groq_key)
        system_prompt = _build_system_prompt(domain)

        # Build context tu chunks
        context_parts = []
        for i, chunk in enumerate(chunks[:5]):
            law = chunk.get("law_name", "Van ban phap luat")
            art = chunk.get("article", "")
            clause = chunk.get("clause", "")
            content = chunk.get("content", "").strip().replace("\n", " ")
            content = " ".join(content.split())[:400]
            ref = f"{law}" + (f", {art}" if art else "") + (f", {clause}" if clause else "")
            context_parts.append(f"[{i+1}] {ref}:\n{content}")

        context_str = "\n\n".join(context_parts)

        # Conflict notice
        conflict_str = ""
        if conflicts:
            conflict_str = (
                f"\n\nLUU Y MAUTHUANPHAP LY: Phat hien {len(conflicts)} mau thuan giua cac van ban. "
                "He thong da uu tien van ban co hieu luc moi nhat.\n"
            )

        # History context (chi 2 turn gan nhat de khong bloat token)
        history_str = ""
        if chat_history:
            recent = chat_history[-4:]  # 2 turns = 4 messages
            history_str = "\n\nLICH SU HOI THOAI GAN NHAT:\n"
            for m in recent:
                role = "Nguoi dung" if m["role"] == "user" else "Tro ly"
                history_str += f"{role}: {m['content'][:300]}\n"

        user_prompt = f"""VAN BAN PHAP LUAT LIEN QUAN:
{context_str}
{conflict_str}{history_str}
---
CAU HOI HIEN TAI: {query}

Hay tra loi chinh xac, co trich dan [so] tuong ung voi cac van ban tren."""

        messages = [
            {"role": "system", "content": system_prompt},  # dynamic persona
            {"role": "user", "content": user_prompt},
        ]

        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.0,
            max_tokens=600,
        )
        return resp.choices[0].message.content.strip()

    # ─────────────────────────────────────────────────────
    # Template-based fallback (khong can API)
    # ─────────────────────────────────────────────────────
    def _generate_template(
        self, query: str, chunks: list[dict], conflicts: list = None
    ) -> str:
        parts = []
        for i, chunk in enumerate(chunks[:5]):
            law = chunk.get("law_name", "van ban phap luat")
            art = chunk.get("article", "")
            clause = chunk.get("clause", "")
            content = chunk.get("content", "").strip().replace("\n", " ")
            content = " ".join(content.split())[:300]
            ref = law + (f", {art}" if art else "") + (f", {clause}" if clause else "")
            if i == 0:
                parts.append(f"Theo {ref}: {content}.")
            else:
                parts.append(f"Bo sung tu {ref}: {content}.")

        if conflicts:
            parts.append(
                f"\nLuu y: Phat hien {len(conflicts)} xung dot giua cac van ban. "
                "He thong da uu tien van ban co hieu luc moi nhat."
            )
        return "\n\n".join(parts)

    # ─────────────────────────────────────────────────────
    # Build citations list
    # ─────────────────────────────────────────────────────
    def _build_citations(self, chunks: list[dict]) -> list[dict]:
        import os as _os
        citations = []
        for chunk in chunks[:5]:
            file_path = chunk.get("file_path") or chunk.get("source_file") or ""
            raw_pdf_url = chunk.get("pdf_url") or ""
            raw_file_name = chunk.get("file_name") or ""

            if not raw_pdf_url and file_path:
                fname = _os.path.basename(str(file_path))
                if fname.lower().endswith(".pdf"):
                    raw_pdf_url = f"/pdf-files/{fname}"
                    raw_file_name = raw_file_name or fname

            citations.append({
                "chunk_id":      str(chunk.get("chunk_id", "")),
                "law_name":      chunk.get("law_name"),
                "article":       chunk.get("article"),
                "clause":        chunk.get("clause"),
                "document_code": chunk.get("document_code"),
                "law_type":      chunk.get("law_type"),
                "content":       chunk.get("content"),
                "effective_date": chunk.get("effective_date"),
                "expiry_date":   chunk.get("expiry_date"),
                "dense_score":   chunk.get("dense_score"),
                "sparse_score":  chunk.get("sparse_score"),
                "rrf_score":     chunk.get("rrf_score"),
                "page_number":   chunk.get("page_number"),
                "file_name":     raw_file_name,
                "pdf_url":       raw_pdf_url,
            })
        return citations
