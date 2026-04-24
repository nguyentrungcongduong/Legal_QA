import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except OSError:
        pass

from retriever.conflict_detector import ConflictDetector

detector = ConflictDetector()

# Giả lập 2 chunks mâu thuẫn
fake_chunks = [
    {
        "chunk_id": "abc-001",
        "content": "Phạt tiền từ 200.000đ đến 400.000đ đối với xe máy vượt đèn đỏ.",
        "law_name": "Nghị định 46/2016/NĐ-CP",
        "document_code": "46/2016/ND-CP",
        "article": "Điều 5",
        "clause": "Khoản 3",
        "effective_date": "2016-08-01"
    },
    {
        "chunk_id": "abc-002",
        "content": "Phạt tiền từ 600.000đ đến 1.000.000đ đối với xe máy vượt đèn đỏ.",
        "law_name": "Nghị định 100/2019/NĐ-CP",
        "document_code": "100/2019/ND-CP",
        "article": "Điều 6",
        "clause": "Khoản 4",
        "effective_date": "2020-01-01"
    }
]

result = detector.detect_and_resolve(fake_chunks)

print(f"Has conflict: {result['has_conflict']}")
print(f"Resolved chunks: {len(result['resolved_chunks'])}")

for c in result["conflicts"]:
    print(f"\nMâu thuẫn: {c['description']}")
    print(f"Loại bỏ:   {c['outdated_source']} — {c['outdated_article']}")
    print(f"Áp dụng:   {c['applied_source']} — {c['applied_article']}")
    print(f"Lý do:     {c['reason']}")
