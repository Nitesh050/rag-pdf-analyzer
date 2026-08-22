from typing import Any, Optional

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
        filter: Optional[dict] = None,
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

        if filter:
            ranked = [
                (score, document)
                for score, document in ranked
                if self._matches(document.metadata, filter)
            ]

        return [
            document
            for score, document in ranked[:k]
        ]

    # ---------------------------------------------------------

    def _matches(
        self,
        metadata: dict,
        filter: dict[str, Any],
    ) -> bool:

        for key, value in filter.items():

            meta_value = metadata.get(key)

            if isinstance(value, (list, tuple, set)):
                if meta_value not in value:
                    return False
            elif meta_value != value:
                return False

        return True

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