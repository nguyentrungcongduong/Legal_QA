"""
guard/query_rewriter.py
Rewrite cau hoi hien tai thanh cau hoi doc lap, day du nguyen.
Dung Groq (Llama 3.3 70B) thay cho OpenAI — FREE 100%.

Tich hop Intent Guard:
  - Phat hien small-talk / xã giao -> giu nguyen, khong rewrite
  - Chi rewrite neu cau hoi la pháp luật thuc su
"""
import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ─── Small-talk detector (rule-based, zero latency) ───────────────────────────
_SMALLTALK_PATTERNS = re.compile(
    r"^\s*("
    r"hello|hi|hey|chào|chao|xin chào|xinchao"
    r"|alo|ơi|oi|howdy|yo|sup"
    r"|cảm ơn|cam on|thanks|thank you|merci|tks|thx"
    r"|ok(ay)?|oke|được rồi|duoc roi|tốt|tot"
    r"|tạm biệt|tam biet|bye|goodbye|ciao"
    r"|bạn là ai|ban la ai|em là gì|em la gi"
    r"|giúp tôi được không|giup toi duoc khong"
    r"|haha|hihi|hehe|lol|:[\)\(]"
    r")\s*[!?.]?\s*$",
    re.IGNORECASE | re.UNICODE,
)

_SYSTEM = (
    "Ban la tro ly xu ly ngon ngu tieng Viet chuyen xu ly cau hoi phap ly. "
    "Nhiem vu duy nhat: viet lai cau hoi PHAP LUAT thanh cau doc lap, ro rang. "
    "Chi tra loi bang chinh cau hoi da viet lai, khong giai thich them gi."
)


class QueryRewriter:
    # Cache: tranh goi LLM lap lai voi cung mot query + history
    _cache: dict[str, str] = {}

    def __init__(self):
        self._client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def rewrite(self, current_query: str, chat_history: list[dict]) -> str:
        """
        Viet lai cau hoi hien tai thanh cau hoi doc lap, day du nguyen.

        Guard layers:
          1. Small-talk rule-based -> tra ve nguyen van (zero LLM cost)
          2. Khong co history -> tra ve nguyen van
          3. Groq rewrite voi prompt co tuong minh chong over-triggering
          4. Fallback: giu nguyen neu Groq loi

        Args:
            current_query: Cau hoi hien tai cua user
            chat_history:  [{role: "user"|"assistant", content: str}]

        Returns:
            Cau hoi da xu ly (hoac nguyen van neu la small-talk / da ro rang)
        """
        q = current_query.strip()

        # ── Layer 1: Small-talk guard (rule-based, instant) ─────────────────
        if _SMALLTALK_PATTERNS.match(q) or len(q) <= 3:
            print(f"[QueryRewriter] SMALL-TALK detected: '{q}' — skip rewrite")
            return q

        # ── Layer 2: No history → no rewrite needed ──────────────────────────
        if not chat_history:
            return q

        # ── Layer 3: LLM rewrite với guard instructions ───────────────────────
        # Chi lay 3 turn gan nhat de tranh token bloat
        recent = chat_history[-6:]
        history_text = "\n".join(
            f"{'Nguoi dung' if m['role'] == 'user' else 'Tro ly'}: {m['content'][:200]}"
            for m in recent
        )

        # Cache key
        cache_key = f"{q}::{history_text[:200]}"
        if cache_key in self._cache:
            print(f"[QueryRewriter] CACHE HIT: '{q}'")
            return self._cache[cache_key]

        prompt = f"""Lich su hoi thoai ve phap luat:
{history_text}

Cau hoi hien tai cua nguoi dung: "{q}"

Nhiệm vụ: Xác định xem cau hoi nay co phai la cau hoi phap luat cap nhap tu hoi thoai truoc do khong.

Quy tắc quan trọng:
- Neu cau hoi la loi CHAO HOI, XA GIAO (hello, xin chao, cam on, ok, bye...) -> Tra ve NGUYEN VAN cau hoi do, TUYET DOI KHONG viet lai thanh cau hoi phap luat
- Neu cau hoi DA RO RANG, day du y nghia phap ly -> Giu nguyen 100%
- Neu cau hoi la follow-up PHAP LUAT (con o to thi sao?, the oto?, muc cao nhat?) -> Viet lai thanh cau hoi phap luat day du, doc lap
- Neu cau hoi KHONG LIEN QUAN den phap luat giao thong VN -> Giu nguyen

Chi tra loi bang duy nhat cau hoi (hoac loi chao), khong giai thich, khong them thong tin."""

        try:
            resp = self._client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=120,
            )
            rewritten = resp.choices[0].message.content.strip().strip('"').strip("'")

            # Sanity check: neu rewritten khong gion chao hoi thi tranh over-trigger
            if _SMALLTALK_PATTERNS.match(rewritten):
                rewritten = q  # tra ve nguyen van

            self._cache[cache_key] = rewritten
            print(f"[QueryRewriter] '{q[:60]}' => '{rewritten[:80]}'")
            return rewritten

        except Exception as e:
            print(f"[QueryRewriter] WARN: {e} — giu nguyen cau hoi goc")
            return q
