import uuid
from pathlib import Path

from langchain_core.documents import Document

from .chunker import DocumentChunker
from .pdf_adapter import PDFAdapter
from ..retrieval.vector_store import VectorStore


class IngestionPipeline:
    """
    Complete ingestion pipeline:
    PDF -> Documents -> Chunks -> ChromaDB
    """

    def __init__(self):
        self.pdf_adapter = PDFAdapter()
        self.chunker = DocumentChunker()
        self.vector_store = VectorStore()

    def ingest_pdf(self, pdf_path: str | Path) -> list[Document]:
        """
        Load a PDF and split it into chunks.
        """

        # Step 1: Load PDF
        documents = self.pdf_adapter.load(pdf_path)

        # Step 2: Split into chunks
        chunks = self.chunker.split(documents)

        if not chunks:
            return []

        # Step 3: Add metadata
        document_id = str(uuid.uuid4())
        filename = Path(pdf_path).name

        for chunk in chunks:
            chunk.metadata["document_id"] = document_id
            chunk.metadata["filename"] = filename

        return chunks

    def run(self, pdf_path: str | Path) -> dict:
        """
        Execute the complete ingestion pipeline.
        """

        chunks = self.ingest_pdf(pdf_path)

        if not chunks:
            return {
                "message": "No content found in PDF.",
                "chunks": 0,
            }

        # Step 4: Store chunks in ChromaDB
        self.vector_store.add_documents(chunks)

        return {
            "message": "PDF indexed successfully.",
            "filename": Path(pdf_path).name,
            "chunks": len(chunks),
        }