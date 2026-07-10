import uuid
from pathlib import Path

from langchain_core.documents import Document

from .chunker import DocumentChunker
from .pdf_adapter import PDFAdapter


class IngestionPipeline:
    def __init__(self):
        self.pdf_adapter = PDFAdapter()
        self.chunker = DocumentChunker()

    def ingest_pdf(self, pdf_path: str | Path) -> list[Document]:
        documents = self.pdf_adapter.load(pdf_path)
        chunks = self.chunker.split(documents)

        if not chunks:
            return []

        document_id = str(uuid.uuid4())
        filename = Path(pdf_path).name

        for chunk in chunks:
            chunk.metadata["document_id"] = document_id
            chunk.metadata["filename"] = filename

        return chunks

    def run(self, pdf_path: str | Path) -> list[Document]:
        """
        Run the full ingestion pipeline for a PDF file.
        """
        return self.ingest_pdf(pdf_path)

