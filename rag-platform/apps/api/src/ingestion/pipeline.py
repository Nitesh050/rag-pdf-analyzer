from pathlib import Path

from langchain_core.documents import Document

from .pdf_adapter import PDFAdapter
from .chunker import DocumentChunker


class IngestionPipeline:

    def __init__(self):

        self.pdf_adapter = PDFAdapter()

        self.chunker = DocumentChunker()

    def ingest_pdf(self, pdf_path: str | Path) -> list[Document]:

        documents = self.pdf_adapter.load(pdf_path)

        chunks = self.chunker.split(documents)

        return chunks

    def run(self, pdf_path: str | Path) -> list[Document]:
        """
        Run the full ingestion pipeline for a PDF file.
        """
        return self.ingest_pdf(pdf_path)