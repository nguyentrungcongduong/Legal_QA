"""
guard/domain_router.py
Bộ điều hướng (Semantic Router) — phân loại câu hỏi theo lĩnh vực pháp luật.

Ưu tiên:
  1. Rule-based fast-path (regex, zero latency, zero LLM cost)
  2. Groq LLM classification (Llama 3.3 70B) nếu rule không quyết định được
  3. Fallback: "giao_thong" (miền mặc định của hệ thống)

Domains:
  giao_thong  — luật giao thông, phạt xe cộ, nồng độ cồn
  dat_dai     — luật đất đai, sổ đỏ, tranh chấp đất, bồi thường đất
  lao_dong    — luật lao động, hợp đồng lao động, lương thưởng, sa thải
  dan_su      — dân sự, hợp đồng, thừa kế, bồi thường thiệt hại
  hinh_su     — hình sự, tội phạm, khởi tố, bắt giam
  small_talk  — chào hỏi, xã giao, không liên quan pháp luật
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# ─── Domain definitions ───────────────────────────────────────────────────────

@dataclass
class DomainInfo:
    code: str          # slug dùng trong code / DB filter
    label_vi: str      # tên tiếng Việt hiển thị trên UI
    emoji: str         # emoji cho UI
    persona: str       # system prompt persona của Generator


DOMAINS: dict[str, DomainInfo] = {
    "giao_thong": DomainInfo(
        code="giao_thong",
        label_vi="Luật Giao thông",
        emoji="🚦",
        persona=(
            "chuyên gia tư vấn Luật Giao thông đường bộ Việt Nam, "
            "am hiểu Nghị định 100/2019/NĐ-CP, Nghị định 123/2021/NĐ-CP và "
            "Luật Giao thông đường bộ 2008"
        ),
    ),
    "dat_dai": DomainInfo(
        code="dat_dai",
        label_vi="Luật Đất đai",
        emoji="🏡",
        persona=(
            "chuyên gia tư vấn Luật Đất đai Việt Nam, "
            "am hiểu Luật Đất đai 2024, Nghị định 43/2014/NĐ-CP và "
            "các quy định về cấp sổ đỏ, tranh chấp, bồi thường đất"
        ),
    ),
    "lao_dong": DomainInfo(
        code="lao_dong",
        label_vi="Luật Lao động",
        emoji="👷",
        persona=(
            "chuyên gia tư vấn Luật Lao động Việt Nam, "
            "am hiểu Bộ luật Lao động 2019, Nghị định 145/2020/NĐ-CP và "
            "các quy định về hợp đồng, sa thải, bảo hiểm xã hội"
        ),
    ),
    "dan_su": DomainInfo(
        code="dan_su",
        label_vi="Luật Dân sự",
        emoji="⚖️",
        persona=(
            "chuyên gia tư vấn Luật Dân sự Việt Nam, "
            "am hiểu Bộ luật Dân sự 2015 và các quy định về "
            "hợp đồng, thừa kế, bồi thường thiệt hại ngoài hợp đồng"
        ),
    ),
    "hinh_su": DomainInfo(
        code="hinh_su",
        label_vi="Luật Hình sự",
        emoji="🔒",
        persona=(
            "chuyên gia tư vấn Luật Hình sự Việt Nam, "
            "am hiểu Bộ luật Hình sự 2015 (sửa đổi 2017) và "
            "Bộ luật Tố tụng Hình sự 2015"
        ),
    ),
    "small_talk": DomainInfo(
        code="small_talk",
        label_vi="Xã giao",
        emoji="👋",
        persona="",
    ),
}

# ─── Fast-path rule-based classification ─────────────────────────────────────

_RULES: list[tuple[re.Pattern, str]] = [
    # Giao thông — keywords
    (re.compile(
        r"đèn đỏ|nồng độ cồn|bằng lái|giấy phép lái|tốc độ|phạt xe|"
        r"xe máy|ô tô|xe tải|xe khách|giao thông|lái xe|tai nạn giao thông|"
        r"vượt đèn|vượt tốc|biển số|đăng kiểm|phù hiệu|dừng đỗ|làn đường|"
        r"không đội mũ|mũ bảo hiểm|nồng|cồn|say rượu|bia rượu|traffic"
        r"|xe được|phương tiện|ngã tư|vạch kẻ đường",
        re.IGNORECASE
    ), "giao_thong"),

    # Đất đai
    (re.compile(
        r"sổ đỏ|sổ hồng|quyền sử dụng đất|giải phóng mặt bằng|thu hồi đất|"
        r"tranh chấp đất|đất đai|quy hoạch đất|bồi thường đất|chuyển nhượng đất|"
        r"cấp sổ|thửa đất|diện tích đất|tách thửa|hộ gia đình sử dụng đất|"
        r"lấn chiếm đất|đất ở|đất nông nghiệp|đất rừng|landlaw",
        re.IGNORECASE
    ), "dat_dai"),

    # Lao động
    (re.compile(
        r"hợp đồng lao động|sa thải|thôi việc|nghỉ việc|lương|thưởng|"
        r"bảo hiểm xã hội|bhxh|bhyt|ốm đau|thai sản|tai nạn lao động|"
        r"người lao động|người sử dụng lao động|công đoàn|đình công|"
        r"chấm dứt hợp đồng|thử việc|tạm hoãn|kỷ luật lao động|"
        r"trợ cấp thất nghiệp|mức lương tối thiểu",
        re.IGNORECASE
    ), "lao_dong"),

    # Hình sự
    (re.compile(
        r"tội phạm|khởi tố|bắt giam|tạm giam|truy nã|hình phạt|tù giam|"
        r"cải tạo không giam giữ|phạt tù|tử hình|nghi can|bị can|bị cáo|"
        r"viện kiểm sát|tòa án hình sự|xét xử|điều tra|gian lận|lừa đảo|"
        r"trộm cắp|cướp|giết người|cố ý gây thương tích|ma túy|tham nhũng",
        re.IGNORECASE
    ), "hinh_su"),

    # Dân sự
    (re.compile(
        r"thừa kế|di chúc|hợp đồng dân sự|bồi thường thiệt hại|"
        r"ly hôn|hôn nhân|nuôi con|hộ tịch|thay đổi tên|khai sinh|"
        r"khai tử|ủy quyền|chứng thực|công chứng|hợp đồng mua bán|"
        r"cho thuê nhà|hợp đồng thuê|dân sự",
        re.IGNORECASE
    ), "dan_su"),

    # Small-talk
    (re.compile(
        r"^(hello|hi|hey|chào|xin chào|alo|cảm ơn|thanks|ok(ay)?|"
        r"bye|tạm biệt|haha|hihi|bạn (là|tên|ở)|em (là|tên))[!?.]?\s*$",
        re.IGNORECASE
    ), "small_talk"),
]


def _rule_classify(query: str) -> str | None:
    """Phân loại nhanh bằng regex — trả None nếu không quyết định được."""
    q = query.strip()
    for pattern, domain in _RULES:
        if pattern.search(q):
            return domain
    return None


# ─── LLM-based fallback classification ───────────────────────────────────────

_CLASSIFY_SYSTEM = (
    "Bạn là chuyên gia phân loại câu hỏi pháp luật Việt Nam. "
    "Nhiệm vụ: xác định lĩnh vực pháp luật của câu hỏi. "
    "Chỉ trả về ĐÚNG MỘT từ trong: "
    "giao_thong | dat_dai | lao_dong | dan_su | hinh_su | small_talk. "
    "Không giải thích, không thêm bất kỳ từ nào khác."
)

_CLASSIFY_FEW_SHOT = """Ví dụ:
Q: Vượt đèn đỏ phạt bao nhiêu? → giao_thong
Q: Sổ đỏ bị mất thì làm sao? → dat_dai
Q: Bị sa thải không có lý do → lao_dong
Q: Thủ tục ly hôn thuận tình → dan_su
Q: Tội trộm cắp bị xử lý thế nào → hinh_su
Q: hello bạn → small_talk
Q: Lấn chiếm hành lang đường bộ → giao_thong
Q: Bồi thường khi thu hồi đất → dat_dai"""


class DomainRouter:
    """
    Phân loại domain của câu hỏi pháp luật.
    Layer 1: regex (instant)
    Layer 2: Groq Llama 3.3 (fast, free)
    Layer 3: fallback → "giao_thong"
    """

    def __init__(self) -> None:
        self._groq_key = os.getenv("GROQ_API_KEY")
        self._cache: dict[str, str] = {}

    def classify(self, query: str) -> str:
        """
        Returns domain code: giao_thong | dat_dai | lao_dong |
                              dan_su | hinh_su | small_talk
        """
        q = query.strip()
        if not q:
            return "small_talk"

        # Layer 1: cache hit
        if q in self._cache:
            return self._cache[q]

        # Layer 2: rule-based fast-path
        rule_result = _rule_classify(q)
        if rule_result:
            print(f"[DomainRouter] RULE → '{rule_result}' for '{q[:50]}'")
            self._cache[q] = rule_result
            return rule_result

        # Layer 3: LLM (chỉ khi cần, không bắt buộc)
        if self._groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=self._groq_key)
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": _CLASSIFY_SYSTEM},
                        {"role": "user", "content": f"{_CLASSIFY_FEW_SHOT}\n\nQ: {q}"},
                    ],
                    temperature=0.0,
                    max_tokens=10,
                )
                raw = resp.choices[0].message.content.strip().lower()
                domain = raw if raw in DOMAINS else "giao_thong"
                print(f"[DomainRouter] LLM → '{domain}' for '{q[:50]}'")
                self._cache[q] = domain
                return domain
            except Exception as e:
                print(f"[DomainRouter] LLM error: {e} — fallback giao_thong")

        # Layer 4: default fallback
        return "giao_thong"

    def get_info(self, domain: str) -> DomainInfo:
        return DOMAINS.get(domain, DOMAINS["giao_thong"])
