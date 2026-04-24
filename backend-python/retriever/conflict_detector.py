import os
from datetime import date
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LLM_JUDGE_PROMPT = """
Bạn là chuyên gia pháp luật. Hãy xác định xem 2 đoạn văn bản pháp luật sau có MÂU THUẪN nhau không.

Mâu thuẫn nghĩa là: cùng một hành vi/tình huống nhưng quy định khác nhau (mức phạt khác, điều kiện khác, kết quả pháp lý khác).

Đoạn 1 ({source1}):
{text1}

Đoạn 2 ({source2}):
{text2}

Chỉ trả lời đúng 1 từ: YES hoặc NO
""".strip()


class ConflictDetector:

    def detect_and_resolve(self, chunks: list[dict]) -> dict:
        if len(chunks) < 2:
            return {
                "resolved_chunks": chunks,
                "conflicts": [],
                "has_conflict": False
            }

        conflicts = []
        removed_ids = set()

        # So sánh từng cặp chunk
        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                a = chunks[i]
                b = chunks[j]

                # Bỏ qua nếu cùng nguồn
                if a.get("document_code") == b.get("document_code"):
                    continue

                # Bỏ qua nếu đã bị loại
                if a.get("chunk_id") in removed_ids or b.get("chunk_id") in removed_ids:
                    continue

                # Check conflict bằng LLM judge
                if not self._is_conflicting(a, b):
                    continue

                # Resolve: giữ bản mới hơn
                date_a = self._parse_date(a.get("effective_date"))
                date_b = self._parse_date(b.get("effective_date"))

                if date_a >= date_b:
                    newer, older = a, b
                else:
                    newer, older = b, a

                removed_ids.add(older.get("chunk_id"))

                conflicts.append({
                    "type": "version_conflict",
                    "description": (
                        f"Mâu thuẫn giữa {a.get('law_name', 'Không rõ')} "
                        f"và {b.get('law_name', 'Không rõ')}"
                    ),
                    "outdated_source": older.get("law_name", "Không rõ"),
                    "outdated_article": older.get("article", ""),
                    "applied_source": newer.get("law_name", "Không rõ"),
                    "applied_article": newer.get("article", ""),
                    "reason": (
                        f"Ưu tiên {newer.get('law_name', 'Không rõ')} "
                        f"(hiệu lực từ {newer.get('effective_date', 'Không rõ')})"
                    )
                })

        resolved = [
            c for c in chunks
            if c.get("chunk_id") not in removed_ids
        ]

        return {
            "resolved_chunks": resolved,
            "conflicts": conflicts,
            "has_conflict": len(conflicts) > 0
        }

    def _is_conflicting(self, chunk_a: dict, chunk_b: dict) -> bool:
        try:
            prompt = LLM_JUDGE_PROMPT.format(
                source1=chunk_a.get("law_name", ""),
                text1=chunk_a.get("content", "")[:500],
                source2=chunk_b.get("law_name", ""),
                text2=chunk_b.get("content", "")[:500],
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # dùng mini cho judge — rẻ hơn
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5
            )
            verdict = response.choices[0].message.content.strip().upper()
            return "YES" in verdict

        except Exception as e:
            print(f"[ConflictDetector] LLM judge error: {e}")
            return False

    def _parse_date(self, date_str: str) -> date:
        if not date_str:
            return date(1900, 1, 1)
        try:
            return date.fromisoformat(str(date_str))
        except Exception:
            return date(1900, 1, 1)
