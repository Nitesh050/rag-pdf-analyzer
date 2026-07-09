from pathlib import Path

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

    def add_documents(
        self,
        documents: list[Document],
    ) -> None:
        """
        Store document chunks inside ChromaDB.
        """

        self.vector_store.add_documents(documents)

    def similarity_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:
        """
        Retrieve the top-k most relevant chunks.
        """

        return self.vector_store.similarity_search(
            query=query,
            k=k,
        )

    def delete_collection(self) -> None:
        """
        Delete the entire collection.
        """

        self.vector_store.delete_collection()