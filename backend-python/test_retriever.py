import sys

from retriever.hybrid_retriever import HybridRetriever


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except OSError:
            pass

    retriever = HybridRetriever()
    query = "Vượt đèn đỏ xe máy bị phạt bao nhiêu tiền?"
    results = retriever.search(query, top_k=5)

    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r['law_name']} — {r['article']}, {r.get('clause', '')}")
        d = r.get("dense_score")
        s = r.get("sparse_score")
        rrf = r.get("rrf_score")
        bits = []
        if d is not None:
            bits.append(f"dense={d:.3f}")
        else:
            bits.append("dense=n/a")
        if s is not None:
            bits.append(f"sparse={s:.3f}")
        else:
            bits.append("sparse=n/a")
        if rrf is not None:
            bits.append(f"rrf={rrf:.4f}")
        print(f"     {' | '.join(bits)}")
        content = r.get("content") or ""
        print(f"     {content[:150]}...")


if __name__ == "__main__":
    main()
