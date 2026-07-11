import uuid

from langchain_core.documents import Document


class MetadataEnricher:
    """
    Adds useful metadata to every chunk before it is stored
    inside the vector database.
    """

    def enrich(
        self,
        chunks: list[Document],
    ) -> list[Document]:

        if not chunks:
            return []

        document_id = str(uuid.uuid4())
        total_chunks = len(chunks)

        for index, chunk in enumerate(chunks):

            metadata = chunk.metadata.copy()

            metadata["document_id"] = document_id

            metadata["chunk_index"] = index

            metadata["total_chunks"] = total_chunks

            metadata["char_count"] = len(
                chunk.page_content
            )

            metadata["word_count"] = len(
                chunk.page_content.split()
            )

            metadata["chunk_id"] = (
                f"{document_id}_{index}"
            )

            chunk.metadata = metadata

        return chunks