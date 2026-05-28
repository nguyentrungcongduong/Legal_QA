"""Unit tests for vehicle RRF boost (no Qdrant)."""
from retriever.vehicle_boost import (
    apply_vehicle_rrf_boost,
    detect_target_article,
)


def test_detect_oto():
    assert detect_target_article(
        "Vượt đèn đỏ xe ô tô bị phạt bao nhiêu?") == "điều 5"


def test_detect_xe_may():
    assert detect_target_article(
        "Vượt đèn đỏ xe máy bị phạt bao nhiêu?") == "điều 6"


def test_detect_none():
    assert detect_target_article("Thủ tục ly hôn thế nào?") is None


def test_rerank_oto():
    chunks = [
        {"article": "Điều 6", "clause": "Khoản 4", "rrf_score": 0.03},
        {"article": "Điều 5", "clause": "Khoản 5", "rrf_score": 0.025},
    ]
    out = apply_vehicle_rrf_boost(
        "xe ô tô vượt đèn đỏ", chunks, boost=0.1, penalty=0.05)
    assert out[0]["article"] == "Điều 5"
    assert out[0]["vehicle_boost"] == 0.1


if __name__ == "__main__":
    test_detect_oto()
    test_detect_xe_may()
    test_detect_none()
    test_rerank_oto()
    print("test_vehicle_boost: OK")
