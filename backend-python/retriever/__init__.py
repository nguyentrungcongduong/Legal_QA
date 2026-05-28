def __getattr__(name: str):
    if name == "HybridRetriever":
        from .hybrid_retriever import HybridRetriever
        return HybridRetriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["HybridRetriever"]
