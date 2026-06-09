"""
generator/generator.py
Sinh cau tra loi tu RAG chunks.
- Khi co Groq API key: dung Llama 3.3 de tao cau tra loi chat luong cao
- Fallback: template-based (khong can API)
"""
import os
import time

_BASE_SYSTEM_TEMPLATE = """Bạn là {persona}.
Nhiệm vụ: Tư vấn pháp luật dựa trên các văn bản được cung cấp.

PHƯƠNG PHÁP TƯ VẤN (Sắc thái câu trả lời):
1. ĐÚNG TRọNG TÂM:
   - Nếu khách hỏi "LÀ GÌ / NGHÌA LÀ GÌ / ĐỊNH NGHĨA": Tập trung giải thích khái niệm, tiêu chí nhận biết (ví dụ: nồng độ cồn bao nhiêu, điều kiện nào). Không liệt kê mức phạt trừ khi được hỏi.
   - Nếu khách hỏi "PHẠT THẾ NÀO / XỬ LÝ SAO / HÌNH PHẠT": Tập trung mức tiền phạt, hình phạt bổ sung (tước bằng, tịch thu), biện pháp khắc phục hậu quả.
   - Nếu khách HỎI TIẾP / YÊU CẦU GIẢI THÍCH: Diễn đạt lại câu trả lời trước đơn giản hơn, dùng ngôn ngữ dễ hiểu.
2. TỔNG HỢP THÔNG TIN: Kết nối các đoạn luật thành bài tư vấn mạch lạc — không sao chép nguyên xi từng chunk rời rạc.
3. NGÔN NGỮ: Văn phong chuyên nghiệp, điềm tĩnh, chính xác của chuyên gia pháp lý.

QUY TẮc CHỐNG ẢO GIÁC (Hallucination Rules):
1. CHỈ sử dụng dữ liệu trong các văn bản được cung cấp. Tuyệt đối không dùng kiến thức cá nhân.
2. Mỗi thông tin khẳng định PHẢI có trích dẫn [số] ở cuối câu, tương ứng với VẬN BẢN số trong danh sách cấp bên dưới.
3. Giữ nguyên các con số (số tiền, số tháng) và đơn vị đo lường.
4. NẾU CÁC VĂN BẢN CUNG CẤP KHÔNG CHỨA THÔNG TIN ĐỂ TRẢ LỜI CÂU HỎI: Dừng lại ngay lập tức và chỉ trả lời đúng 1 câu: "Hệ thống chưa có đủ dữ liệu cụ thể về trường hợp này." TUYỆT ĐỐI KHÔNG tóm tắt hoặc chép lại các nội dung không liên quan trong văn bản chỉ để có câu trả lời.
5. CHÚ Ý QUAN TRỌNG VỀ ĐỐI TƯỢNG XỬ PHẠT THEO NGHỊ ĐỊNH 100/2019: Trong các đoạn trích (chunks) có thể bị mất bối cảnh tên Điều. Hãy tự suy luận dựa trên số Điều:
   - Điều 5: Áp dụng cho Xe ô tô và các loại xe tương tự ô tô.
   - Điều 6: Áp dụng cho Xe mô tô, xe gắn máy, xe máy điện.
   - Điều 7: Áp dụng cho Máy kéo, xe máy chuyên dùng.
   - Điều 8: Áp dụng cho Xe đạp, xe đạp máy, xe thô sơ.
   - Điều 9: Áp dụng cho Người đi bộ.
   (Lưu ý: Hãy linh hoạt hiểu các thuật ngữ đời thường tương đương với thuật ngữ pháp lý, ví dụ: 'vượt đèn đỏ' = 'không chấp hành tín hiệu đèn', 'xe ô tô' = Điều 5, 'xe máy' = Điều 6).

Kiểm tra cuối cùng: Câu trả lời có đúng trọng tâm, có trích dẫn, và tổng hợp mạch lạc không?"""


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
        domain: str | None = None,
        # "auto" | "groq" | "gemini" | "openai" | "template"
        model_preference: str = "auto",
    ) -> dict:
        citations = self._build_citations(chunks)

        if not chunks:
            return {
                "answer": f"Không tìm thấy căn cứ pháp lý phù hợp cho câu hỏi: '{query}'.",
                "citations": [],
                "model_used": "none",
            }

        pref = (model_preference or "auto").lower()
        print(f"[Generator] model_preference='{pref}'")

        answer = None
        model_used = "template"

        # ── Chọn model cụ thể: KHÔNG fallback sang model khác ───────────────────
        if pref == "groq":
            if self._groq_key:
                try:
                    answer = self._generate_with_groq(
                        query, chunks, conflicts, chat_history, domain=domain)
                    model_used = "groq"
                except Exception as e:
                    print(f"[Generator] Groq error: {e}")
            if answer is None:
                return {"answer": "⚠️ Groq API không khả dụng. Vui lòng chọn model khác hoặc dùng **Auto**.",
                        "citations": [], "model_used": "error"}

        elif pref == "gemini":
            gemini_key = os.getenv(
                "GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if gemini_key:
                try:
                    answer = self._generate_with_gemini(
                        query, chunks, conflicts, chat_history, domain=domain, api_key=gemini_key)
                    model_used = "gemini"
                except Exception as e:
                    print(f"[Generator] Gemini error: {e}")
            if answer is None:
                return {"answer": "⚠️ Gemini API không khả dụng. Vui lòng chọn model khác hoặc dùng **Auto**.",
                        "citations": [], "model_used": "error"}

        elif pref == "openai":
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                try:
                    answer = self._generate_with_openai(
                        query, chunks, conflicts, chat_history, domain=domain, api_key=openai_key)
                    model_used = "openai"
                except Exception as e:
                    print(f"[Generator] OpenAI error: {e}")
            if answer is None:
                return {"answer": "⚠️ OpenAI API không khả dụng. Vui lòng chọn model khác hoặc dùng **Auto**.",
                        "citations": [], "model_used": "error"}

        elif pref == "template":
            answer = self._generate_template(query, chunks, conflicts)
            return {"answer": answer, "citations": citations, "model_used": "template"}

        else:  # pref == "auto" — cascade Groq → Gemini → OpenAI → Template
            if self._groq_key:
                try:
                    answer = self._generate_with_groq(
                        query, chunks, conflicts, chat_history, domain=domain)
                    model_used = "groq"
                except Exception as e:
                    print(f"[Generator] Groq error: {e} — trying Gemini")

            if answer is None:
                gemini_key = os.getenv(
                    "GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                if gemini_key:
                    try:
                        answer = self._generate_with_gemini(
                            query, chunks, conflicts, chat_history, domain=domain, api_key=gemini_key)
                        model_used = "gemini"
                    except Exception as e:
                        print(f"[Generator] Gemini error: {e} — trying OpenAI")

            if answer is None:
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key:
                    try:
                        answer = self._generate_with_openai(
                            query, chunks, conflicts, chat_history, domain=domain, api_key=openai_key)
                        model_used = "openai"
                    except Exception as e:
                        print(
                            f"[Generator] OpenAI error: {e} — fallback to template")

            if answer is None:
                answer = self._generate_template(query, chunks, conflicts)
                return {"answer": answer, "citations": citations, "model_used": "template"}

        # ── Post-process: reindex [1][2]... theo thứ tự xuất hiện trong text ──
        answer, citations = self._reindex_citations(answer, citations)
        return {"answer": answer, "citations": citations, "model_used": model_used}

    def _reindex_citations(self, answer: str, citations: list[dict]) -> tuple[str, list[dict]]:
        """
        Reindex [N] trong answer theo thứ tự xuất hiện đầu tiên.
        VD: nếu LLM viết "[2] ... [1] ... [3]" thì:
          - [2] → [1] (xuất hiện đầu)
          - [1] → [2] (xuất hiện thứ hai)
          - [3] → [3] (giữ nguyên)
        Đồng thời sắp xếp lại mảng citations theo mapping mới.

        Cũng xử lý dạng LLM viết [1, 3] hoặc [1,3] → normalize thành [1][3].
        """
        import re

        # --- Bước normalize: [1, 3] → [1][3] ---
        def expand_multi_citation(m):
            inner = m.group(1)  # VD: "1, 3" hoặc "1,3"
            nums = [n.strip() for n in inner.split(',')]
            if all(n.isdigit() for n in nums) and len(nums) > 1:
                return ''.join(f'[{n}]' for n in nums)
            return m.group(0)  # giữ nguyên nếu không phải số

        answer = re.sub(r'\[([^\[\]]+)\]', expand_multi_citation, answer)

        # Tìm tất cả [N] theo thứ tự xuất hiện trong text
        mentions = re.findall(r'\[(\d+)\]', answer)
        old_order = []
        for m in mentions:
            idx = int(m)
            if idx not in old_order and 1 <= idx <= len(citations):
                old_order.append(idx)

        if not old_order:
            return answer, []

        if old_order == list(range(1, len(old_order) + 1)):
            # Thu tu da dung, chi can cat bo cac citations chua duoc nhac toi
            return answer, citations[:len(old_order)]

        # Tao mapping: old_num → new_num
        mapping = {old: new for new, old in enumerate(old_order, start=1)}

        # Dung placeholder de tranh reindex nhieu lan (VD: [2]→[1] roi [1]→[2])
        # Buoc 1: thay [N] bang ##N## tam thoi
        temp = re.sub(r'\[(\d+)\]', lambda m: f'##{m.group(1)}##', answer)

        # Buoc 2: thay ##N## bang [new_N]
        def replace_placeholder(m):
            old_num = int(m.group(1))
            new_num = mapping.get(old_num, old_num)
            return f'[{new_num}]'

        reindexed_answer = re.sub(r'##(\d+)##', replace_placeholder, temp)

        # Sap xep lai citations array theo old_order
        reindexed_citations = []
        for old_num in old_order:
            if 1 <= old_num <= len(citations):
                reindexed_citations.append(citations[old_num - 1])

        # Loại bỏ các citations thừa không được LLM sử dụng trong text
        # để tránh UI hiển thị danh sách dài có các bài trùng lặp.

        return reindexed_answer, reindexed_citations

    # ─────────────────────────────────────────────────────
    # Groq-based generation (chat luong cao)
    # ─────────────────────────────────────────────────────

    def _generate_with_groq(
        self,
        query: str,
        chunks: list[dict],
        conflicts: list = None,
        chat_history: list[dict] = None,
        domain: str | None = None,
    ) -> str:
        from groq import Groq, RateLimitError
        client = Groq(api_key=self._groq_key)
        system_prompt = _build_system_prompt(domain)

        # Build context
        context_parts = []
        for i, chunk in enumerate(chunks[:5]):
            law = chunk.get("law_name", "Văn bản pháp luật")
            art = chunk.get("article", "")
            cls = chunk.get("clause", "")
            content = chunk.get("content", "").strip().replace("\n", " ")
            # đủ dài để chứa a), b), c)...
            content = " ".join(content.split())[:1200]
            ref = f"{law}" + (f", {art}" if art else "") + \
                (f", {cls}" if cls else "")

            # Add metadata to help LLM answer temporal/metadata questions
            eff_date = chunk.get("effective_date")
            exp_date = chunk.get("expiry_date")
            meta_str = ""
            if eff_date and eff_date != "None":
                meta_str += f" | Hiệu lực từ: {eff_date}"
            if exp_date and exp_date != "None":
                meta_str += f" | Hết hiệu lực: {exp_date}"

            context_parts.append(
                f"VĂN BẢN [{i+1}]: {ref}{meta_str}\nNỘI DUNG: {content}")

        context_str = "\n\n".join(context_parts)

        conflict_str = ""
        if conflicts:
            conflict_str = (
                f"\n\nLƯŨ Ý XUNG ĐỘT PHÁP LÝ: Phát hiện {len(conflicts)} xung đột giữa các văn bản. "
                "Hệ thống đã ưu tiên văn bản có hiệu lực mới nhất.\n"
            )

        history_str = ""
        if chat_history:
            recent = chat_history[-4:]
            history_str = "\n\nLỊCH SỬ TƯ VẤN GẦN NHẤT:\n"
            for m in recent:
                role = "Khách" if m["role"] == "user" else "Trợ lý"
                history_str += f"{role}: {m['content'][:300]}\n"

        user_prompt = f"""DƯỚI ĐÂY LÀ DANH SÁCH VĂN BẢN PHÁP LUẬT XÁC THỰC:
{context_str}
{conflict_str}{history_str}

CÂU HỎI HIỆN TẠI: "{query}"

YÊU CẦU NGHIÊM NGẶT VỀ NỘI DUNG VÀ ĐỊNH DẠNG:
1. ĐÁNH GIÁ MỨC ĐỘ LIÊN QUAN: Đọc kỹ các văn bản. (Cho phép linh hoạt: ngôn ngữ đời thường như 'vượt đèn đỏ' tương đương 'không chấp hành đèn tín hiệu'; 'xe mô tô' và 'xe máy' là cùng loại phương tiện theo Nghị định 100).
   - Nếu câu hỏi là HỎI TIẾP / LIÊN QUAN đến nội dung đã tư vấn trong LỊCH SỬ: hãy dùng thông tin từ lịch sử trò chuyện để trả lời, KHÔNG cần trích dẫn thêm nếu đã có đủ.
   - Chỉ khi KHÔNG CÓ thông tin trong cả văn bản lẫn lịch sử, mới viết: "Hệ thống chưa có đủ dữ liệu cụ thể về trường hợp này."
   - KHI CÓ XUNG ĐỘT NHIỀU ĐIỀU LUẬT cùng đề cập mức phạt tương tự: ƯU TIÊN theo hai nguyên tắc:
     a) Ưu tiên VĂN BẢN CÓ NGÀY HIỆU LỰC MỚI HƠN (NĐ 168/2024 > NĐ 123/2021 > NĐ 100/2019).
     b) Ưu tiên ĐIỀU LUẬT tương ứng với PHƯƠNG TIỆN trong câu hỏi: xe máy/mô tô → Điều 6 (NĐ 168) hoặc Điều 6 (NĐ 100), xe kéo/máy kéo → Điều 7, xe đạp → Điều 9 (NĐ 168) hoặc Điều 8 (NĐ 100), người đi bộ → Điều 10 (NĐ 168) hoặc Điều 9 (NĐ 100). Bỏ qua các Điều không khớp phương tiện.
2. Phân tích ý định câu hỏi rồi trả lời đúng trọng tâm:
   - Hỏi MỨC PHẠT / XỬ LÝ: giữ NGUYÊN con số tiền phạt, thời gian tước bằng, v.v. từ văn bản.
   - Hỏi ĐỊNH NGHĨA / QUY TRÌNH: tóm tắt rõ ràng, giữ nguyên các điều kiện cụ thể a), b), c).
   - HỎI TIẾP / GIẢI THÍCH LẠI (VD: "thế còn xe mô tô thì sao", "nói thêm về điều đó", "thế nếu... thì sao"): ưu tiên dùng nội dung lịch sử tư vấn để trả lời trực tiếp.
3. ĐỘ CHÍNH XÁC TUYỆT ĐỐI:
   - Chỉ sử dụng thông tin có trong VĂN BẢN hoặc LỊCH SỬ TƯ VẤN. TUYỆT ĐỐI KHÔNG bịa thêm chi tiết không có.
   - Giữ NGUYÊN XI các con số (tiền phạt, thời hạn), điều kiện (a, b, c...) từ văn bản gốc.
   - Nếu thông tin bị cắt ngắn ("...") thì ghi "(xem chi tiết tại văn bản gốc)" thay vì tự suy đoán.
4. TRÍCH DẪN BẮT BUỘC: MỖI CÂU khẳng định từ VĂN BẢN PHÁP LUẬT PHẢI kết thúc bằng [số] tương ứng.
   - CHỈ dùng [N] của VĂN BẢN [N] có chứa đúng mức phạt / điều khoản bạn đang nêu (không trích dẫn [1] nếu nội dung lấy từ [2] hoặc [3]).
   - VĂN BẢN [1] → [1], VĂN BẢN [2] → [2], VĂN BẢN [3] → [3], v.v.
   - Nếu trả lời từ lịch sử hội thoại (không có văn bản mới), không cần thêm [số] nhưng phải nói rõ "Như đã tư vấn ở trên,..."
   - Ví dụ ĐÚNG: "Bị phạt từ 6.000.000 đến 8.000.000 đồng [1]. Tước GPLX từ 10 đến 12 tháng [2]."
5. TUYỆT ĐỐI không bỏ sót [số] sau bất kỳ câu khẳng định nào từ văn bản.
6. Tổng hợp mạch lạc, ngắn gọn — ưu tiên chính xác hơn là văn vẻ."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        # Thử model lớn trước, fallback sang model nhỏ khi bị rate-limit
        models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
        last_err = None
        for i, model_name in enumerate(models_to_try):
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=800,
                    timeout=25,      # 25s timeout/call — tránh block vô hạn
                )
                if model_name != "llama-3.3-70b-versatile":
                    print(f"[Generator] Groq fallback model: {model_name}")
                return resp.choices[0].message.content.strip()
            except RateLimitError as e:
                last_err = e
                print(
                    f"[Generator] Groq rate-limit on {model_name}, trying next...")
                if i < len(models_to_try) - 1:
                    # pause nhỏ giữa retries — tránh cascade rate-limit
                    time.sleep(1)
                continue
            except Exception as e:
                raise e  # lỗi khác thì throw để outer catch xử lý
        raise last_err  # tất cả models đều bị rate-limit

    # ─────────────────────────────────────────────────────
    # Gemini Flash fallback (khi Groq rate-limit)
    # ─────────────────────────────────────────────────────
    def _generate_with_gemini(
        self,
        query: str,
        chunks: list[dict],
        conflicts: list = None,
        chat_history: list[dict] = None,
        domain: str | None = None,
        api_key: str = "",
    ) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Build context (cùng logic như Groq)
        context_parts = []
        for i, chunk in enumerate(chunks[:5]):
            law = chunk.get("law_name", "Văn bản pháp luật")
            art = chunk.get("article", "")
            cls = chunk.get("clause", "")
            content = chunk.get("content", "").strip().replace("\n", " ")
            content = " ".join(content.split())[:1200]
            ref = f"{law}" + (f", {art}" if art else "") + \
                (f", {cls}" if cls else "")

            # Add metadata to help LLM answer temporal/metadata questions
            eff_date = chunk.get("effective_date")
            exp_date = chunk.get("expiry_date")
            meta_str = ""
            if eff_date and eff_date != "None":
                meta_str += f" | Hiệu lực từ: {eff_date}"
            if exp_date and exp_date != "None":
                meta_str += f" | Hết hiệu lực: {exp_date}"

            context_parts.append(
                f"VĂN BẢN [{i+1}]: {ref}{meta_str}\nNỘI DUNG: {content}")

        context_str = "\n\n".join(context_parts)
        conflict_str = ""
        if conflicts:
            conflict_str = f"\n\nLƯU Ý XUNG ĐỘT: {len(conflicts)} xung đột phát hiện, ưu tiên văn bản mới nhất.\n"

        history_str = ""
        if chat_history:
            recent = chat_history[-4:]
            history_str = "\n\nLỊCH SỬ TƯ VẤN GẦN NHẤT:\n"
            for m in recent:
                role = "Khách" if m["role"] == "user" else "Trợ lý"
                history_str += f"{role}: {m['content'][:300]}\n"

        system_prompt = _build_system_prompt(domain)
        user_prompt = f"""DƯỚI ĐÂY LÀ DANH SÁCH VĂN BẢN PHÁP LUẬT XÁC THỰC:
{context_str}
{conflict_str}{history_str}

CÂU HỎI HIỆN TẠI: "{query}"

YÊU CẦU NGHIÊM NGẶT VỀ NỘI DUNG VÀ ĐỊNH DẠNG:
1. ĐÁNH GIÁ MỨC ĐỘ LIÊN QUAN: Đọc kỹ các văn bản. (Cho phép linh hoạt: 'vượt đèn đỏ' = 'không chấp hành đèn tín hiệu'; 'xe mô tô' và 'xe máy' là cùng loại phương tiện theo Nghị định 100).
   - Nếu câu hỏi là HỎI TIẾP / LIÊN QUAN đến nội dung đã tư vấn trong LỊCH SỬ: hãy dùng thông tin từ lịch sử để trả lời, không cần trích dẫn thêm nếu đã có đủ.
   - Chỉ khi KHÔNG CÓ thông tin trong cả văn bản lẫn lịch sử, mới viết: "Hệ thống chưa có đủ dữ liệu cụ thể về trường hợp này."
   - KHI CÓ XUNG ĐỘT NHIỀU ĐIỀU LUẬT (Điều 5 và Điều 6 cùng đề cập mức phạt tương tự): ƯU TIÊN chọn Điều tương ứng với phương tiện được nhắc trong câu hỏi (ô tô → Điều 5, xe máy → Điều 6, xe kéo/máy kéo → Điều 7, xe đạp → Điều 8). Bỏ qua các Điều không khớp phương tiện.
   - HỎI TIẾP (VD: "thế mô tô thì sao", "nói thêm", "thế nếu... thì sao"): ưu tiên dùng lịch sử tư vấn để trả lời trực tiếp.
3. ĐỘ CHÍNH XÁC TUYỆT ĐỐI:
   - Chỉ dùng thông tin có trong VĂN BẢN hoặc LỊCH SỬ TƯ VẤN. TUYỆT ĐỐI KHÔNG bịa thêm.
   - Giữ NGUYÊN XI các con số, điều kiện a), b), c)... từ văn bản gốc.
   - Nếu thông tin bị cắt ngắn thì ghi "(xem chi tiết tại văn bản gốc)".
4. TRÍCH DẪN BẮT BUỘC: MỖI CÂU khẳng định từ VĂN BẢN PHẢI kết thúc bằng [số].
   - CHỈ dùng [N] của VĂN BẢN [N] có chứa đúng mức phạt / điều khoản bạn đang nêu.
   - VĂN BẢN [1] → [1], VĂN BẢN [2] → [2], v.v.
   - Nếu trả lời từ lịch sử hội thoại, không cần [số] nhưng phải nói "Như đã tư vấn ở trên,..."
   - Ví dụ ĐÚNG: "Bị phạt từ 200.000-300.000 đồng [1]. Ngoài ra có thể bị tước GPLX [2]."
5. Tổng hợp mạch lạc, ngắn gọn — ưu tiên chính xác hơn văn vẻ."""

        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0,
                max_output_tokens=800,
            ),
        )
        return resp.text.strip()

    # ─────────────────────────────────────────────────────
    # OpenAI GPT-4o-mini fallback
    # ─────────────────────────────────────────────────────
    def _generate_with_openai(
        self,
        query: str,
        chunks: list[dict],
        conflicts: list = None,
        chat_history: list[dict] = None,
        domain: str | None = None,
        api_key: str = "",
    ) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        context_parts = []
        for i, chunk in enumerate(chunks[:5]):
            law = chunk.get("law_name", "Văn bản pháp luật")
            art = chunk.get("article", "")
            cls = chunk.get("clause", "")
            content = chunk.get("content", "").strip().replace("\n", " ")
            content = " ".join(content.split())[:1200]
            ref = f"{law}" + (f", {art}" if art else "") + \
                (f", {cls}" if cls else "")

            # Add metadata to help LLM answer temporal/metadata questions
            eff_date = chunk.get("effective_date")
            exp_date = chunk.get("expiry_date")
            meta_str = ""
            if eff_date and eff_date != "None":
                meta_str += f" | Hiệu lực từ: {eff_date}"
            if exp_date and exp_date != "None":
                meta_str += f" | Hết hiệu lực: {exp_date}"

            context_parts.append(
                f"VĂN BẢN [{i+1}]: {ref}{meta_str}\nNỘI DUNG: {content}")

        context_str = "\n\n".join(context_parts)
        conflict_str = ""
        if conflicts:
            conflict_str = f"\n\nLƯU Ý XUNG ĐỘT: {len(conflicts)} xung đột, ưu tiên văn bản mới nhất.\n"

        history_str = ""
        if chat_history:
            recent = chat_history[-4:]
            history_str = "\n\nLỊCH SỬ TƯ VẤN GẦN NHẤT:\n"
            for m in recent:
                role = "Khách" if m["role"] == "user" else "Trợ lý"
                history_str += f"{role}: {m['content'][:300]}\n"

        user_prompt = f"""DƯỚI ĐÂY LÀ DANH SÁCH VĂN BẢN PHÁP LUẬT XÁC THỰC:
{context_str}
{conflict_str}{history_str}

CÂU HỎI HIỆN TẠI: "{query}"

YÊU CẦU NGHIÊM NGẶT VỀ ĐỊNH DẠNG:
1. ĐÁNH GIÁ MỨC ĐỘ LIÊN QUAN: Đọc kỹ các văn bản. (Cho phép linh hoạt: 'vượt đèn đỏ' = 'không chấp hành đèn tín hiệu'; 'xe mô tô' và 'xe máy' là cùng loại phương tiện theo Nghị định 100).
   - Nếu câu hỏi là HỎI TIẾP / LIÊN QUAN đến nội dung đã tư vấn trong LỊCH SỬ: hãy dùng thông tin từ lịch sử để trả lời, không cần trích dẫn thêm nếu đã có đủ.
   - Chỉ khi KHÔNG CÓ thông tin trong cả văn bản lẫn lịch sử, mới viết: "Hệ thống chưa có đủ dữ liệu cụ thể về trường hợp này."
   - KHI CÓ XUNG ĐỘT NHIỀU ĐIỀU LUẬT (Điều 5 và Điều 6 cùng đề cập mức phạt tương tự): ƯU TIÊN chọn Điều tương ứng với phương tiện được nhắc trong câu hỏi (ô tô → Điều 5, xe máy → Điều 6, xe kéo/máy kéo → Điều 7, xe đạp → Điều 8). Bỏ qua các Điều không khớp phương tiện.
2. Phân tích ý định câu hỏi:
   - HỎI TIẾP (VD: "thế mô tô thì sao", "nói thêm", "thế nếu... thì sao"): ưu tiên dùng lịch sử tư vấn để trả lời trực tiếp.
3. TRÍCH DẪN BẮT BUỘC: MỖI CÂU khẳng định từ VĂN BẢN PHẢI kết thúc bằng [số] tương ứng.
   - CHỈ dùng [N] của VĂN BẢN [N] có chứa đúng mức phạt / điều khoản bạn đang nêu.
   - VĂN BẢN [1] → [1], VĂN BẢN [2] → [2], VĂN BẢN [3] → [3], v.v.
   - Nếu trả lời từ lịch sử hội thoại, không cần [số] nhưng phải nói "Như đã tư vấn ở trên,..."
   - Ví dụ ĐÚNG: "Bị phạt từ 200.000-300.000 đồng [1]. Ngoài ra có thể bị tước GPLX [2]."
4. Tổng hợp mạch lạc, không sao chép nguyên xi."""

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _build_system_prompt(domain)},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=800,
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
            ref = law + (f", {art}" if art else "") + \
                (f", {clause}" if clause else "")
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
            file_path = chunk.get("file_path") or chunk.get(
                "source_file") or ""
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
