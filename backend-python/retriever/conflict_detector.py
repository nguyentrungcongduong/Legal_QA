import os
import re
from datetime import date
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

_LEGAL_KEYWORDS = {
    "phạt", "tiền", "mức", "khoản", "điều", "nghị định", "tước",
    "giấy phép", "nồng độ", "cồn", "vi phạm", "xử phạt", "hành chính",
    "tốc độ", "bảo hiểm", "mũ", "đèn", "vạch", "biển", "đường"
}


class ConflictDetector:

    def detect_and_resolve(self, chunks: list[dict]) -> dict:
        if len(chunks) < 2:
            return {"resolved_chunks": chunks, "conflicts": [], "has_conflict": False}

        conflicts = []
        removed_ids = set()

        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                a = chunks[i]
                b = chunks[j]

                if a.get("document_code") == b.get("document_code"):
                    continue
                if a.get("chunk_id") in removed_ids or b.get("chunk_id") in removed_ids:
                    continue

                if not self._is_conflicting(a, b):
                    continue

                date_a = self._parse_date(a.get("effective_date"))
                date_b = self._parse_date(b.get("effective_date"))
                newer, older = (a, b) if date_a >= date_b else (b, a)
                removed_ids.add(older.get("chunk_id"))

                conflicts.append({
                    "type": "version_conflict",
                    "description": (
                        f"Mâu thuẫn giữa {a.get('law_name', 'Không rõ')} "
                        f"và {b.get('law_name', 'Không rõ')}"
                    ),
                    "outdated_source":  older.get("law_name", "Không rõ"),
                    "outdated_article": older.get("article", ""),
                    "applied_source":   newer.get("law_name", "Không rõ"),
                    "applied_article":  newer.get("article", ""),
                    "reason": (
                        f"Ưu tiên {newer.get('law_name', 'Không rõ')} "
                        f"(hiệu lực từ {newer.get('effective_date', 'Không rõ')})"
                    )
                })

        resolved = [c for c in chunks if c.get("chunk_id") not in removed_ids]
        return {"resolved_chunks": resolved, "conflicts": conflicts, "has_conflict": len(conflicts) > 0}

    def _is_conflicting(self, chunk_a: dict, chunk_b: dict) -> bool:
        text_a = chunk_a.get("content", "").lower()
        text_b = chunk_b.get("content", "").lower()

        words_a = set(text_a.split())
        words_b = set(text_b.split())
        common_legal = (words_a & _LEGAL_KEYWORDS) & (words_b & _LEGAL_KEYWORDS)

        if len(common_legal) < 3:
            return False

        if "phạt" in common_legal and "tiền" in common_legal:
            nums_a = set(re.findall(r'\d[\d.]+', text_a))
            nums_b = set(re.findall(r'\d[\d.]+', text_b))
            if len(nums_a) > 0 and len(nums_b) > 0 and len(nums_a & nums_b) == 0:
                return True

        return False

    def _parse_date(self, date_str: str) -> date:
        if not date_str:
            return date(1900, 1, 1)
        try:
            return date.fromisoformat(str(date_str))
        except Exception:
            return date(1900, 1, 1)
