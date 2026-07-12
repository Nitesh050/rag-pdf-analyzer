from langchain_core.documents import Document

from .bm25 import BM25Retriever
from .fusion import ReciprocalRankFusion
from .vector_store import VectorStore


class HybridRetriever:
    """
    Hybrid Retriever

    Combines:
    1. Semantic Search (Chroma)
    2. BM25 Keyword Search
    3. Reciprocal Rank Fusion
    """

    def __init__(self):

        self.vector_store = VectorStore()

        self.bm25 = BM25Retriever()

        self.fusion = ReciprocalRankFusion()

    # ---------------------------------------------------------

    def build_keyword_index(self):

        """
        Build BM25 from all documents stored in Chroma.
        """

        documents = self.vector_store.get_all_documents()

        self.bm25.build_index(documents)

    # ---------------------------------------------------------

    def semantic_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:

        return self.vector_store.similarity_search(
            query=query,
            k=k,
        )

    # ---------------------------------------------------------

    def keyword_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:

        return self.bm25.retrieve(
            query=query,
            k=k,
        )

    # ---------------------------------------------------------

    def retrieve(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:

        semantic_results = self.semantic_search(
            query=query,
            k=k,
        )

        keyword_results = self.keyword_search(
            query=query,
            k=k,
        )

        fused_results = self.fusion.fuse(
            ranked_lists=[
                semantic_results,
                keyword_results,
            ],
            top_k=k,
        )

        return fused_results