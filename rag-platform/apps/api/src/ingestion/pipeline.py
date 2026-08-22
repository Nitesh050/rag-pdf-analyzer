import uuid
from pathlib import Path

from langchain_core.documents import Document

from .chunking.chunker import DocumentChunker
from .pdf_adapter import PDFAdapter
from ..dependencies import get_retrieval_manager
from ..retrieval.retrieval_manager import RetrievalManager


class IngestionPipeline:
    """
    Complete ingestion pipeline:
    PDF -> Documents -> Chunks -> ChromaDB -> BM25 index
    """

    def __init__(self, retrieval_manager: RetrievalManager | None = None):
        self.pdf_adapter = PDFAdapter()
        self.chunker = DocumentChunker()
        self.retrieval_manager = retrieval_manager or get_retrieval_manager()
        self.vector_store = self.retrieval_manager.vector_store

    def ingest_pdf(
        self,
        pdf_path: str | Path,
        document_id: str | None = None,
        content_hash: str | None = None,
    ) -> list[Document]:
        """
        Load a PDF and split it into chunks.
        """

        # Step 1: Load PDF
        documents = self.pdf_adapter.load(pdf_path)

        # Step 2: Split into chunks. document_id is generated once here
        # (not inside the chunker/enricher) so it's consistent across
        # every chunk's `document_id` field and its `chunk_id` prefix.
        document_id = document_id or str(uuid.uuid4())
        chunks = self.chunker.split(documents, document_id=document_id)

        if not chunks:
            return []

        # Step 3: Add metadata
        filename = Path(pdf_path).name

        for chunk in chunks:
            chunk.metadata["filename"] = filename
            if content_hash:
                chunk.metadata["content_hash"] = content_hash

        return chunks

    def run(self, pdf_path: str | Path, content_hash: str | None = None) -> dict:
        """
        Execute the complete ingestion pipeline.
        """

        # Skip re-ingesting content that's already indexed (e.g. the same
        # file uploaded twice), rather than creating duplicate chunks.
        if content_hash:
            existing = self.vector_store.get_by_content_hash(content_hash)

            if existing:
                return {
                    "message": "Document already indexed.",
                    "filename": Path(pdf_path).name,
                    "document_id": existing[0].metadata.get("document_id"),
                    "chunks": 0,
                }

        document_id = str(uuid.uuid4())
        chunks = self.ingest_pdf(
            pdf_path,
            document_id=document_id,
            content_hash=content_hash,
        )

        if not chunks:
            return {
                "message": "No content found in PDF.",
                "chunks": 0,
            }

        # Step 4: Store chunks in ChromaDB
        self.vector_store.add_documents(chunks)

        # Step 5: Rebuild the BM25 keyword index so hybrid search
        # (used by RAGChain via RetrievalManager) can see the new chunks.
        self.retrieval_manager.build_indexes()

        return {
            "message": "PDF indexed successfully.",
            "filename": Path(pdf_path).name,
            "document_id": document_id,
            "chunks": len(chunks),
        }