import re


class ChunkingUtils:
    """
    Collection of helper methods used throughout the
    chunking pipeline.
    """

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Replace multiple spaces/newlines with a single space.
        """

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def count_words(text: str) -> int:
        """
        Count the number of words.
        """

        return len(text.split())

    @staticmethod
    def count_characters(text: str) -> int:
        """
        Count total characters.
        """

        return len(text)

    @staticmethod
    def count_sentences(text: str) -> int:
        """
        Rough sentence count.
        """

        return len(
            re.findall(
                r"[.!?]+",
                text,
            )
        )

    @staticmethod
    def count_paragraphs(text: str) -> int:
        """
        Count non-empty paragraphs.
        """

        paragraphs = [
            p
            for p in text.split("\n\n")
            if p.strip()
        ]

        return len(paragraphs)

    @staticmethod
    def remove_extra_newlines(text: str) -> str:
        """
        Collapse multiple blank lines into one.
        """

        return re.sub(
            r"\n{2,}",
            "\n\n",
            text,
        )

    @staticmethod
    def remove_multiple_spaces(text: str) -> str:
        """
        Collapse consecutive spaces.
        """

        return re.sub(
            r"[ ]{2,}",
            " ",
            text,
        )

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Perform basic text cleaning.
        """

        text = ChunkingUtils.remove_extra_newlines(text)

        text = ChunkingUtils.remove_multiple_spaces(text)

        return text.strip()

    @staticmethod
    def is_empty(text: str) -> bool:
        """
        Check if text contains any useful information.
        """

        return len(text.strip()) == 0