from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

import re


class BM25Retriever:
    """
    BM25 keyword-based retriever.
    """

    def __init__(self):

        self.documents: list[Document] = []

        self.tokenized_documents: list[list[str]] = []

        self.index: BM25Okapi | None = None

    # ---------------------------------------------------------

    def tokenize(
        self,
        text: str,
    ) -> list[str]:

        text = text.lower()

        text = re.sub(
            r"[^\w\s]",
            " ",
            text,
        )

        return text.split()

    # ---------------------------------------------------------

    def build_index(
        self,
        documents: list[Document],
    ) -> None:

        self.documents = documents

        self.tokenized_documents = [
            self.tokenize(doc.page_content)
            for doc in documents
        ]

        self.index = BM25Okapi(
            self.tokenized_documents
        )

    # ---------------------------------------------------------

    def retrieve(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:

        if self.index is None:
            return []

        tokens = self.tokenize(query)

        scores = self.index.get_scores(tokens)

        ranked = sorted(
            zip(scores, self.documents),
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            document
            for score, document in ranked[:k]
        ]

    # ---------------------------------------------------------

    def rebuild(
        self,
        documents: list[Document],
    ) -> None:

        self.build_index(documents)

    # ---------------------------------------------------------

    def clear(self):

        self.documents = []

        self.tokenized_documents = []

        self.index = None