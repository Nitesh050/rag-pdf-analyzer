from langchain_core.documents import Document


class DocumentAnalyzer:
    """
    Analyzes a document collection and returns useful statistics
    that will later be used for adaptive chunking.
    """

    def analyze(
        self,
        documents: list[Document],
    ) -> dict:

        if not documents:
            return {
                "pages": 0,
                "characters": 0,
                "words": 0,
                "sentences": 0,
                "paragraphs": 0,
                "avg_page_length": 0,
                "avg_words_per_page": 0,
                "largest_page": 0,
                "smallest_page": 0,
                "empty_pages": 0,
            }

        total_characters = 0
        total_words = 0
        total_sentences = 0
        total_paragraphs = 0

        largest_page = 0
        smallest_page = float("inf")
        empty_pages = 0

        for document in documents:

            text = document.page_content.strip()

            if not text:
                empty_pages += 1
                continue

            characters = len(text)
            words = len(text.split())

            # Very simple sentence estimation
            sentences = (
                text.count(".")
                + text.count("?")
                + text.count("!")
            )

            # Count non-empty paragraphs
            paragraphs = len(
                [
                    p
                    for p in text.split("\n\n")
                    if p.strip()
                ]
            )

            total_characters += characters
            total_words += words
            total_sentences += sentences
            total_paragraphs += paragraphs

            largest_page = max(
                largest_page,
                characters,
            )

            smallest_page = min(
                smallest_page,
                characters,
            )

        page_count = len(documents)

        if smallest_page == float("inf"):
            smallest_page = 0

        return {

            "pages": page_count,

            "characters": total_characters,

            "words": total_words,

            "sentences": total_sentences,

            "paragraphs": total_paragraphs,

            "avg_page_length":
                total_characters // max(page_count, 1),

            "avg_words_per_page":
                total_words // max(page_count, 1),

            "largest_page":
                largest_page,

            "smallest_page":
                smallest_page,

            "empty_pages":
                empty_pages,
        }