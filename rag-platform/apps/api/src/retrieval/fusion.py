from langchain_core.documents import Document


class ReciprocalRankFusion:
    """
    Combines multiple ranked retrieval results using
    Reciprocal Rank Fusion (RRF).

    RRF Score:
        score += 1 / (k + rank)

    Default k = 60 (recommended in the original paper).
    """

    def __init__(
        self,
        k: int = 60,
    ):
        self.k = k

    def fuse(
        self,
        ranked_lists: list[list[Document]],
        top_k: int = 5,
    ) -> list[Document]:

        scores = {}
        documents = {}

        # --------------------------------------
        # Calculate RRF Score
        # --------------------------------------

        for ranked_list in ranked_lists:

            for rank, document in enumerate(ranked_list):

                # Unique identifier for each chunk
                doc_id = (
                    document.metadata.get("document_id"),
                    document.metadata.get("page"),
                    hash(document.page_content),
                )

                documents[doc_id] = document

                scores[doc_id] = scores.get(doc_id, 0)

                scores[doc_id] += 1 / (
                    self.k + rank + 1
                )

        # --------------------------------------
        # Sort by score
        # --------------------------------------

        ranked_documents = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            documents[doc_id]
            for doc_id, _ in ranked_documents[:top_k]
        ]