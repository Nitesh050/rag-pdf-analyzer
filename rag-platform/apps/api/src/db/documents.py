import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from ..models.document import Document
from ..models.user import User


def parse_document_id(value: str | None) -> uuid.UUID | None:
    """The document_id from a request as a UUID, or None if absent or malformed."""
    try:
        return uuid.UUID(value) if value else None
    except ValueError:
        return None


def record_document(
    db: Session,
    owner: User,
    document_id: str,
    content_hash: str,
    chunk_count: int,
    ingestion_version: int | None,
    filename: str | None = None,
    source_url: str | None = None,
    storage_path: str | Path | None = None,
) -> Document:
    """
    Make sure an indexed document has a row in Postgres, keyed by the same
    document_id the vector store uses. Re-uploads update the existing row.
    The vector store remains the source of the chunks for now.
    """
    document = db.get(Document, uuid.UUID(document_id))

    if document is None:
        document = Document(
            id=uuid.UUID(document_id),
            owner_id=owner.id,
            source_type="pdf" if filename else "url",
            content_hash=content_hash,
        )
        db.add(document)

    document.filename = filename
    document.source_url = source_url
    if storage_path is not None:
        path = Path(storage_path)
        document.storage_path = str(path)
        document.size_bytes = path.stat().st_size if path.exists() else None
        document.mime_type = "application/pdf" if path.suffix.lower() == ".pdf" else None
    document.status = "ready"
    document.ingestion_version = ingestion_version
    if chunk_count:
        document.chunk_count = chunk_count
    document.indexed_at = document.indexed_at or datetime.now(timezone.utc)
    document.deleted_at = None

    db.commit()
    return document
