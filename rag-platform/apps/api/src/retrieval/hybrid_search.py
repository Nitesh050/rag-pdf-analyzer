from langchain_core.documents import Document

from .bm25 import BM25Retriever
from .fusion import ReciprocalRankFusion
from .vector_store import VectorStore


class HybridRetriever:
    """
    Hybrid Retriever
    Combines:
    1. Semantic Search (vector store)
    2. BM25 Keyword Search
    3. Reciprocal Rank Fusion
    """

    def __init__(self, overfetch_multiplier: int = 3, min_fetch_k: int = 10):
        self.vector_store = VectorStore()
        self.bm25 = BM25Retriever()
        self.fusion = ReciprocalRankFusion()

        # How aggressively to overfetch from each retriever before fusing.
        # RRF needs a wider candidate pool than the final top_k to work well.
        self.overfetch_multiplier = overfetch_multiplier
        self.min_fetch_k = min_fetch_k

        self._index_built = False

    # ---------------------------------------------------------
    def build_keyword_index(self):
        """
        Build BM25 from all documents stored in the vector store.
        """
        documents = self.vector_store.get_all_documents()

        if not documents:
            # BM25Okapi divides by the average document length, which
            # is undefined for an empty corpus (e.g. before the first
            # upload). Leave the index unbuilt; retrieve() falls back
            # to semantic-only results in that case.
            self.bm25.clear()
            self._index_built = False
            return

        self.bm25.build_index(documents)
        self._index_built = True

    # ---------------------------------------------------------
    def semantic_search(
        self,
        query: str,
        k: int = 5,
        filter: dict | None = None,
    ) -> list[Document]:
        if k <= 0:
            raise ValueError(f"k must be a positive integer, got {k}")

        return self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filter,
        )

    # ---------------------------------------------------------
    def keyword_search(
        self,
        query: str,
        k: int = 5,
        filter: dict | None = None,
    ) -> list[Document]:
        if k <= 0:
            raise ValueError(f"k must be a positive integer, got {k}")

        if not self._index_built:
            raise RuntimeError(
                "BM25 index has not been built yet. "
                "Call build_keyword_index() before keyword_search()."
            )

        return self.bm25.retrieve(
            query=query,
            k=k,
            filter=filter,
        )

    # ---------------------------------------------------------
    def _compute_fetch_k(self, k: int) -> int:
        """
        Determine how many candidates to pull from each individual
        retriever before fusing. RRF needs a larger candidate pool
        than the final desired top_k to surface documents that rank
        moderately well across multiple retrievers.
        """
        return max(k * self.overfetch_multiplier, self.min_fetch_k)

    # ---------------------------------------------------------
    def retrieve(
        self,
        query: str,
        k: int = 5,
        fetch_k: int | None = None,
        filter: dict | None = None,
    ) -> list[Document]:
        """
        Retrieve top-k documents using hybrid search.

        Args:
            query: Search query.
            k: Number of final fused results to return.
            fetch_k: Number of candidates to pull from each individual
                retriever before fusion. Defaults to
                max(k * overfetch_multiplier, min_fetch_k) if not provided.
            filter: optional metadata filter (e.g. {"document_id": ...})
                applied to both the semantic and keyword retrievers.
        """
        if k <= 0:
            raise ValueError(f"k must be a positive integer, got {k}")

        fetch_k = fetch_k or self._compute_fetch_k(k)

        semantic_results = self.semantic_search(
            query=query,
            k=fetch_k,
            filter=filter,
        )

        if not self._index_built:
            # No keyword index yet (e.g. nothing has been ingested,
            # or the corpus was empty on the last build). Fall back
            # to semantic-only results instead of erroring out.
            return semantic_results[:k]

        keyword_results = self.keyword_search(
            query=query,
            k=fetch_k,
            filter=filter,
        )

        fused_results = self.fusion.fuse(
            ranked_lists=[
                semantic_results,
                keyword_results,
            ],
            top_k=k,  # truncate to the caller's desired k only at the end
        )
        return fused_results