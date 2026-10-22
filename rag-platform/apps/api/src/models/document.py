import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, Timestamped
from .user import User

SOURCE_TYPES = ("pdf", "url", "youtube")
STATUSES = ("uploaded", "processing", "ready", "failed")


class Document(Timestamped, Base):
    """
    An uploaded source. Its id is the document_id used in the vector store
    and sent by the frontend with each question.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
    )
    source_type: Mapped[str] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    filename: Mapped[str | None] = mapped_column(String)
    source_url: Mapped[str | None] = mapped_column(String)
    storage_path: Mapped[str | None] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str | None] = mapped_column(String)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    page_count: Mapped[int | None]
    status: Mapped[str] = mapped_column(String, default="uploaded", server_default="uploaded")
    error_message: Mapped[str | None] = mapped_column(String)
    ingestion_version: Mapped[int | None]
    chunk_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User] = relationship()

    @property
    def display_name(self) -> str:
        return self.title or self.filename or self.source_url or str(self.id)
