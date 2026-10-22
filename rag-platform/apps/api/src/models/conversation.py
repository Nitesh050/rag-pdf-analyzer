import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, Timestamped


class Conversation(Timestamped, Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
    )
    # The document the chat is about; NULL searches every document.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"),
    )
    title: Mapped[str | None] = mapped_column(String)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"),
    )
    role: Mapped[str] = mapped_column(String)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(String)

    # Assistant messages only.
    standalone_question: Mapped[str | None] = mapped_column(String)
    intent: Mapped[str | None] = mapped_column(String)
    refused: Mapped[bool | None]
    model: Mapped[str | None] = mapped_column(String)
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]
    latency_ms: Mapped[int | None]

    status: Mapped[str] = mapped_column(String, default="ok", server_default="ok")
    error_message: Mapped[str | None] = mapped_column(String)
    # clock_timestamp(), not now(): a question and its answer are saved in
    # the same transaction, where now() is identical, so ordering by
    # created_at could put the answer first.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.clock_timestamp(), server_default=func.now(),
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    sources: Mapped[list["MessageSource"]] = relationship(
        order_by="MessageSource.source_number",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MessageSource(Base):
    """A source shown under an answer (a chunk it cited)."""

    __tablename__ = "message_sources"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True,
    )
    source_number: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"),
    )
    chunk_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("chunks.id", ondelete="SET NULL"),
    )
    page: Mapped[int | None]
    page_end: Mapped[int | None]
    cited: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
