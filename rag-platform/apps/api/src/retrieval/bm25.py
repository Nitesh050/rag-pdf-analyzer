from typing import Any, Optional

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
import snowballstemmer

import re

# Function words that carry no topic. Left in, they dominate BM25 scores
# for natural-language questions ("what does it mean to ...") and pull in
# chunks that merely share the phrasing of the question.
STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been
before being below between both but by can could did do does doing down during
each few for from further had has have having he her here hers herself him
himself his how i if in into is it its itself just me more most my myself no
nor not of off on once only or other our ours ourselves out over own same she
should so some such than that the their theirs them themselves then there these
they this those through to too under until up very was we were what when where
which while who whom why will with would you your yours yourself yourselves
""".split())


class BM25Retriever:
    """
    BM25 keyword-based retriever.
    """

    def __init__(self):

        self.documents: list[Document] = []

        self.tokenized_documents: list[list[str]] = []

        self.index: BM25Okapi | None = None

        self.stemmer = snowballstemmer.stemmer("english")

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

        # Stem so "saturate" in a question matches "saturating" in the text.
        return self.stemmer.stemWords(
            [word for word in text.split() if word not in STOPWORDS]
        )

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

        # Chunks sharing no query term score 0; returning them anyway would
        # hand fusion an arbitrary ranking of irrelevant chunks.
        ranked = sorted(
            (
                (score, document)
                for score, document in zip(scores, self.documents)
                if score > 0
            ),
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