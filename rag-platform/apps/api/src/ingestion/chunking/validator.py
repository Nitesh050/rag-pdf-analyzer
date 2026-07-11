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
        max_special_ratio: float = 0.40,
    ):

        self.min_characters = min_characters
        self.min_words = min_words
        self.max_special_ratio = max_special_ratio

    def validate(
        self,
        chunks: list[Document],
    ) -> list[Document]:

        valid_chunks = []

        for chunk in chunks:

            if self._is_valid(chunk):

                valid_chunks.append(chunk)

        return valid_chunks

    def _is_valid(
        self,
        chunk: Document,
    ) -> bool:

        text = chunk.page_content.strip()

        # Empty chunk
        if not text:
            return False

        # Too short
        if len(text) < self.min_characters:
            return False

        # Too few words
        if len(text.split()) < self.min_words:
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