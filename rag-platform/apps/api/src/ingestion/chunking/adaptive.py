class AdaptiveChunkSizer:
    """
    Determines the optimal chunk size and overlap
    based on document statistics.
    """

    def __init__(self):

        self.min_chunk_size = 500
        self.max_chunk_size = 2000

        self.min_overlap = 100
        self.max_overlap = 400

    def calculate(
        self,
        stats: dict,
    ) -> tuple[int, int]:

        avg_page_length = stats["avg_page_length"]
        total_pages = stats["pages"]

        # Small PDFs
        if total_pages <= 5:

            chunk_size = 700

        # Medium PDFs
        elif total_pages <= 20:

            chunk_size = 1000

        # Large Books
        elif total_pages <= 100:

            chunk_size = 1400

        # Huge Documents
        else:

            chunk_size = 1800

        # Prevent chunk size larger than average page
        if avg_page_length < chunk_size:

            chunk_size = max(
                self.min_chunk_size,
                int(avg_page_length * 0.8),
            )

        chunk_size = min(
            max(chunk_size, self.min_chunk_size),
            self.max_chunk_size,
        )

        overlap = int(chunk_size * 0.20)

        overlap = min(
            max(overlap, self.min_overlap),
            self.max_overlap,
        )

        return chunk_size, overlap