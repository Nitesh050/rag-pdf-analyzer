from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_chroma import Chroma

from .embedder import Embedder


class VectorStore:
    """
    Handles storing and retrieving document embeddings using ChromaDB.
    """

    def __init__(
        self,
        persist_directory: str = "data/chroma_db",
        collection_name: str = "rag_documents",
    ):

        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        self.embedder = Embedder()

        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embedder.embeddings,
            persist_directory=persist_directory,
        )

    # ---------------------------------------------------
    # INSERT
    # ---------------------------------------------------

    def add_documents(
        self,
        documents: list[Document],
    ) -> None:
        """
        Store document chunks inside ChromaDB.
        """

        self.vector_store.add_documents(documents)

    # ---------------------------------------------------
    # SEARCH
    # ---------------------------------------------------

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> list[Document]:
        """
        Semantic similarity search.
        """

        return self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filter,
        )

    # ---------------------------------------------------
    # GET ALL DOCUMENTS
    # ---------------------------------------------------

    def get_all_documents(self) -> list[Document]:
        """
        Retrieve every stored chunk.
        Useful for summarization.
        """

        data = self.vector_store.get(
            include=["documents", "metadatas"]
        )

        documents = []

        docs = data.get("documents", [])
        metas = data.get("metadatas", [])

        for text, metadata in zip(docs, metas):

            documents.append(
                Document(
                    page_content=text,
                    metadata=metadata,
                )
            )

        return documents

    # ---------------------------------------------------
    # DOCUMENT FILTER
    # ---------------------------------------------------

    def get_document(
        self,
        document_id: str,
    ) -> list[Document]:
        """
        Retrieve one uploaded document.
        """

        return self.similarity_search(
            query="",
            k=1000,
            filter={
                "document_id": document_id,
            },
        )

    # ---------------------------------------------------
    # PAGE FILTER
    # ---------------------------------------------------

    def get_page(
        self,
        page: int,
    ) -> list[Document]:

        return self.similarity_search(
            query="",
            k=100,
            filter={
                "page": page,
            },
        )

    # ---------------------------------------------------
    # FILE FILTER
    # ---------------------------------------------------

    def get_filename(
        self,
        filename: str,
    ) -> list[Document]:

        return self.similarity_search(
            query="",
            k=1000,
            filter={
                "filename": filename,
            },
        )

    # ---------------------------------------------------
    # LIST DOCUMENTS
    # ---------------------------------------------------

    def list_documents(self) -> list[str]:
        """
        Return every unique uploaded file.
        """

        data = self.vector_store.get(
            include=["metadatas"]
        )

        names = set()

        for metadata in data["metadatas"]:

            if metadata.get("filename"):

                names.add(
                    metadata["filename"]
                )

        return sorted(list(names))

    # ---------------------------------------------------
    # DELETE FILE
    # ---------------------------------------------------

    def delete_document(
        self,
        filename: str,
    ) -> None:
        """
        Delete one uploaded PDF.
        """

        self.vector_store.delete(
            where={
                "filename": filename,
            }
        )

    # ---------------------------------------------------
    # DELETE EVERYTHING
    # ---------------------------------------------------

    def delete_collection(self) -> None:
        """
        Delete entire database.
        """

        self.vector_store.delete_collection()