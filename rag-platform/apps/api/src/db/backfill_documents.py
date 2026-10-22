"""
Create Postgres rows for documents that were indexed before the database
existed. Safe to run more than once.

    cd apps/api
    .venv/bin/python -m src.db.backfill_documents
"""

from collections import Counter
from pathlib import Path

from ..core.security import get_local_user
from ..retrieval.vector_store import VectorStore
from .documents import record_document
from .session import get_sessionmaker


def main() -> None:
    vector_store = VectorStore()
    records = vector_store.document_records()
    chunk_counts = Counter(
        m.get("document_id")
        for m in vector_store.vector_store.get(include=["metadatas"])["metadatas"]
    )

    with get_sessionmaker()() as db:
        owner = get_local_user(db)

        for record in records:
            filename = record.get("filename") or ""
            is_url = filename.startswith(("http://", "https://"))

            document = record_document(
                db,
                owner,
                document_id=record["document_id"],
                content_hash=record.get("content_hash") or f"unknown:{record['document_id']}",
                chunk_count=chunk_counts[record["document_id"]],
                ingestion_version=record.get("ingestion_version"),
                filename=None if is_url else filename,
                source_url=filename if is_url else None,
                storage_path=None if is_url else Path("uploads") / filename,
            )
            print(f"  {document.display_name}: {document.chunk_count} chunks")

    print(f"{len(records)} documents recorded")


if __name__ == "__main__":
    main()
