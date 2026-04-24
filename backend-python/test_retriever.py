"""
test_retriever.py - kiem thu HybridRetriever + DomainRouter nhieu domain
Chay: .venv/Scripts/python.exe test_retriever.py
"""
import sys

# Đảm bảo UTF-8 trên Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except OSError:
        pass

from retriever.hybrid_retriever import HybridRetriever
from guard.domain_router import DomainRouter

# ============================================================
print("Đang khởi tạo HybridRetriever (load model embedding)...")
retriever = HybridRetriever()
router   = DomainRouter()
print("Sẵn sàng!\n")
# ============================================================

test_queries = [
    "Vượt đèn đỏ xe máy bị phạt bao nhiêu?",
    "Tranh chấp đất đai giải quyết ở đâu?",
    "Người lao động bị sa thải sai có được bồi thường không?",
    "Ly hôn thì tài sản chung chia thế nào?",
    "Lấn chiếm đất hành lang giao thông phạt bao nhiêu?",   # cross-domain
]

for query in test_queries:
    print("=" * 65)
    print(f"Query: {query}")

    domain = router.classify(query)
    info   = router.get_info(domain)
    print(f"Detected domain: {info.emoji} {info.label_vi} ({domain})")

    chunks = retriever.search(query, top_k=3, domain=domain)

    if not chunks:
        print("  ⚠️  Không tìm được chunk nào!")
    else:
        for i, c in enumerate(chunks, 1):
            dense  = c.get("dense_score")
            sparse = c.get("sparse_score")
            rrf    = c.get("rrf_score")
            d_str  = f"{dense:.3f}"  if dense  is not None else "n/a"
            s_str  = f"{sparse:.3f}" if sparse is not None else "n/a"
            r_str  = f"{rrf:.4f}"   if rrf    is not None else "n/a"
            content = (c.get("content") or "").replace("\n", " ")
            print(
                f"  [{i}] {c.get('law_name', 'N/A')} — {c.get('article', '')} "
                f"{c.get('clause', '')}"
            )
            print(f"       dense={d_str} | sparse={s_str} | rrf={r_str}")
            print(f"       {content[:120]}...")

print("\nTest hoàn tất!")
