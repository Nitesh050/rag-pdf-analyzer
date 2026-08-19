import os
from functools import lru_cache

from .retrieval.retrieval_manager import RetrievalManager

# Reranking is opt-in: it loads a cross-encoder model (network fetch on
# first use, then a real model forward pass per query), so it shouldn't
# be forced on for every process start (tests, scripts, etc).
RERANKER_MODEL = os.getenv("RERANKER_MODEL")


@lru_cache
def get_retrieval_manager() -> RetrievalManager:
    """
    Process-wide RetrievalManager singleton.

    Shared between ingestion (which rebuilds the in-memory BM25 index
    after new documents are stored) and the RAG chain (which queries
    hybrid search + reranking), since BM25Retriever keeps its index
    in memory per instance rather than in Chroma.
    """
    return RetrievalManager(reranker_model=RERANKER_MODEL)
