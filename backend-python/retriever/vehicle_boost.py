"""
Boost / penalize RRF scores when the query names a vehicle type (NĐ 100/168 style).
Aligns VĂN BẢN [1] with the correct Điều before the generator runs.
"""
from __future__ import annotations

import os
import re
import unicodedata

# Điều 5–10: mức phạt theo loại phương tiện (giao thông)
_TRAFFIC_ARTICLES = tuple(f"điều {i}" for i in range(5, 11))

# (target article prefix, query keywords) — thứ tự ưu tiên: cụm dài trước
_VEHICLE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("điều 5", ("xe ô tô", "ô tô", "ôtô", "oto", "xe hơi", "xe con", "xe 4 bánh")),
    ("điều 6", ("xe gắn máy", "xe máy", "xe may",
     "mô tô", "motô", "xe điện", "xe 2 bánh")),
    ("điều 7", ("máy kéo", "may keo", "xe máy chuyên dùng", "xe chuyên dùng")),
    ("điều 8", ("xe đạp máy", "xe đạp", "xe dap", "xe thô sơ", "xe tho so")),
    ("điều 9", ("người đi bộ", "nguoi di bo", "đi bộ", "di bo")),
    # NĐ 168 dùng Điều 10 cho người đi bộ, nhưng keyword trùng với Điều 9
    # → không thể phân biệt qua keyword, bỏ qua để tránh dead-code
]

_DEFAULT_BOOST = float(os.getenv("VEHICLE_RRF_BOOST", "0.07"))
_DEFAULT_PENALTY = float(os.getenv("VEHICLE_RRF_PENALTY", "0.04"))


def _normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def detect_target_article(query: str) -> str | None:
    """Return article prefix e.g. 'điều 5' if query mentions a vehicle type."""
    q = _normalize(query)
    for article, keywords in _VEHICLE_RULES:
        for kw in sorted(keywords, key=len, reverse=True):
            if _normalize(kw) in q:
                return article
    return None


def _article_key(article: str | None) -> str:
    """Extract 'điều N' key for comparison.
    
    NOTE: _normalize() strips all diacritics (NFD), so we cannot match the
    word 'điều' in the normalized string. Instead we just extract the number
    and rebuild the key using the un-normalized prefix.
    """
    if not article:
        return ""
    # Search for a number anywhere in the article string (e.g. "Điều 5", "Khoản 5")
    m = re.search(r"\d+", article)
    return f"điều {m.group()}" if m else ""


def apply_vehicle_rrf_boost(
    query: str,
    chunks: list[dict],
    *,
    boost: float = _DEFAULT_BOOST,
    penalty: float = _DEFAULT_PENALTY,
) -> list[dict]:
    """
    Re-rank chunks after RRF merge when query names a vehicle.
    Matching article gets +boost; other Điều 5–10 get -penalty.
    """
    target = detect_target_article(query)
    if not target or not chunks:
        return chunks

    target_key = _article_key(target)
    out: list[dict] = []

    for ch in chunks:
        item = dict(ch)
        art_key = _article_key(item.get("article"))
        if not art_key:
            out.append(item)
            continue

        if art_key == target_key:
            item["rrf_score"] = (item.get("rrf_score") or 0.0) + boost
            item["vehicle_boost"] = boost
        elif art_key in _TRAFFIC_ARTICLES:
            item["rrf_score"] = (item.get("rrf_score") or 0.0) - penalty
            item["vehicle_boost"] = -penalty
        out.append(item)

    out.sort(key=lambda x: -(x.get("rrf_score") or 0.0))
    # ascii() escapes non-ASCII chars → safe on Windows cp1252 console
    print(
        f"[Retriever] vehicle_boost target={ascii(target)} "
        f"boost={boost} penalty={penalty}",
        flush=True,
    )
    return out
