from langchain_core.documents import Document

from .adaptive import AdaptiveChunkSizer
from .analyzer import DocumentAnalyzer
from .metadata import MetadataEnricher
from .splitter import DocumentSplitter
from .validator import ChunkValidator


class DocumentChunker:
    """
    Main orchestrator for the document chunking pipeline.

    Workflow:
        1. Analyze document
        2. Determine adaptive chunk size
        3. Split document
        4. Validate chunks
        5. Enrich metadata
    """

    def __init__(self):

        self.analyzer = DocumentAnalyzer()

        self.chunk_sizer = AdaptiveChunkSizer()

        self.validator = ChunkValidator()

        self.metadata = MetadataEnricher()

    def split(
        self,
        documents: list[Document],
    ) -> list[Document]:

        if not documents:
            return []

        # ----------------------------------
        # Step 1 : Analyze document
        # ----------------------------------

        stats = self.analyzer.analyze(documents)

        # ----------------------------------
        # Step 2 : Calculate chunk size
        # ----------------------------------

        chunk_size, overlap = self.chunk_sizer.calculate(
            stats
        )

        # ----------------------------------
        # Step 3 : Build splitter
        # ----------------------------------

        splitter = DocumentSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
        )

        # ----------------------------------
        # Step 4 : Split
        # ----------------------------------

        chunks = splitter.split(documents)

        # ----------------------------------
        # Step 5 : Validate
        # ----------------------------------

        chunks = self.validator.validate(chunks)

        # ----------------------------------
        # Step 6 : Metadata enrichment
        # ----------------------------------

        chunks = self.metadata.enrich(chunks)

        return chunks