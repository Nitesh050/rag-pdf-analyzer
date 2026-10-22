import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

EMBEDDING_DIMENSIONS = 768  # nomic-embed-text


class Chunk(Base):
    """
    One chunk of a document: text, metadata and (once embedded) its vector.
    Not written by the app yet; the vector store is still Chroma.
    """

    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "{document_id}_{chunk_index}"
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
    )
    chunk_index: Mapped[int]
    page: Mapped[int | None]
    start_char: Mapped[int | None]
    text: Mapped[str] = mapped_column(String)
    char_count: Mapped[int]
    word_count: Mapped[int]
    ingestion_version: Mapped[int]
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    embedding_model: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
