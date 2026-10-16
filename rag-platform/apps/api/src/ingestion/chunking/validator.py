import re

from langchain_core.documents import Document


class ChunkValidator:
    """
    Validates document chunks before they are stored
    in the vector database.
    """

    def __init__(
        self,
        min_characters: int = 100,
        min_words: int = 20,
        keep_min_words: int = 5,
        max_special_ratio: float = 0.40,
    ):

        # Below min_characters / min_words a chunk is "short" and gets merged
        # into a same-page neighbour. A short chunk with no neighbour (e.g. a
        # slide whose only text is one OCR'd sentence) is still kept if it
        # has keep_min_words; titles like "QUESTION 3" are dropped.
        self.min_characters = min_characters
        self.min_words = min_words
        self.keep_min_words = keep_min_words
        self.max_special_ratio = max_special_ratio

    def validate(
        self,
        chunks: list[Document],
    ) -> list[Document]:

        valid_chunks = []

        for chunk in self._merge_short_chunks(chunks):

            if self._is_valid(chunk):

                valid_chunks.append(chunk)

        return valid_chunks

    def _merge_short_chunks(
        self,
        chunks: list[Document],
    ) -> list[Document]:
        """
        Attach short chunks to a neighbour on the same page instead of
        letting validation drop them. The splitter often cuts a heading
        ("## Preparing Data") off from the text it introduces; merged
        forward, the heading stays with its section. Short chunks with no
        same-page neighbour are left for _is_valid to reject.
        """

        merged: list[Document] = []
        pending: Document | None = None

        for chunk in chunks:

            if pending is not None:

                if self._same_page(pending, chunk):
                    chunk = self._join(pending, chunk)
                else:
                    self._attach_to_previous(merged, pending)

                pending = None

            if self._is_short(chunk):
                pending = chunk
            else:
                merged.append(chunk)

        if pending is not None:
            self._attach_to_previous(merged, pending)

        return merged

    def _attach_to_previous(
        self,
        merged: list[Document],
        chunk: Document,
    ) -> None:

        if merged and self._same_page(merged[-1], chunk):
            merged[-1] = self._join(merged[-1], chunk)
        else:
            merged.append(chunk)

    @staticmethod
    def _join(
        first: Document,
        second: Document,
    ) -> Document:

        head = first.page_content.strip()
        tail = second.page_content.strip()

        # Chunk overlap may already have copied the short text across.
        if head in tail:
            text = tail
        elif tail in head:
            text = head
        else:
            text = f"{head}\n\n{tail}"

        return Document(page_content=text, metadata=first.metadata.copy())

    @staticmethod
    def _same_page(
        first: Document,
        second: Document,
    ) -> bool:

        return (
            first.metadata.get("source") == second.metadata.get("source")
            and first.metadata.get("page") == second.metadata.get("page")
        )

    def _is_short(
        self,
        chunk: Document,
    ) -> bool:

        text = chunk.page_content.strip()

        return (
            len(text) < self.min_characters
            or len(text.split()) < self.min_words
        )

    def _is_valid(
        self,
        chunk: Document,
    ) -> bool:

        text = chunk.page_content.strip()

        # Empty chunk
        if not text:
            return False

        # Too few words to carry content
        if len(text.split()) < self.keep_min_words:
            return False

        # Mostly special characters
        if self._special_character_ratio(text) > self.max_special_ratio:
            return False

        return True

    def _special_character_ratio(
        self,
        text: str,
    ) -> float:

        special = len(
            re.findall(
                r"[^a-zA-Z0-9\s]",
                text,
            )
        )

        return special / max(len(text), 1)