from langchain_core.documents import Document
from sentence_transformers import CrossEncoder


class Reranker:
    """
    Cross Encoder based reranker.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
    ):

        self.model = CrossEncoder(model_name)

    # ---------------------------------------------------

    def rerank(
        self,
        query: str,
        documents: list[Document],
        top_k: int = 5,
    ) -> list[Document]:

        if not documents:
            return []

        sentence_pairs = [
            (
                query,
                doc.page_content,
            )
            for doc in documents
        ]

        scores = self.model.predict(
            sentence_pairs
        )

        ranked = sorted(
            zip(scores, documents),
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            doc
            for score, doc in ranked[:top_k]
        ]