"""
Re-process documents indexed by an older ingestion pipeline.

    cd apps/api
    .venv/bin/python -m src.ingestion.reindex           # re-index stale documents
    .venv/bin/python -m src.ingestion.reindex --dry-run # only list them

PDFs are re-read from uploads/<filename>; web pages are re-fetched from
their URL. Each keeps its document_id. Restart the API afterwards so its
in-memory keyword index picks up the new chunks.
"""

import argparse
from pathlib import Path

from .pipeline import INGESTION_VERSION, IngestionPipeline

UPLOAD_DIR = Path("uploads")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    pipeline = IngestionPipeline()
    records = pipeline.vector_store.document_records()
    stale = [r for r in records if r.get("ingestion_version") != INGESTION_VERSION]

    print(f"{len(records)} documents, {len(stale)} indexed by an older version (current: {INGESTION_VERSION})")

    for record in stale:
        filename = record.get("filename") or ""
        content_hash = record.get("content_hash")
        label = f"{filename or record.get('source')} (version {record.get('ingestion_version')})"

        if not content_hash:
            print(f"  skip  {label}: no content_hash, can't re-index in place")
            continue

        if filename.startswith(("http://", "https://")):
            source = filename
            rerun = lambda: pipeline.run_web(source, content_hash=content_hash)
        elif (UPLOAD_DIR / filename).exists():
            source = UPLOAD_DIR / filename
            rerun = lambda: pipeline.run(source, content_hash=content_hash)
        else:
            print(f"  skip  {label}: source file not found in {UPLOAD_DIR}/")
            continue

        if args.dry_run:
            print(f"  stale {label}")
            continue

        result = rerun()
        print(f"  done  {label}: {result['message']} ({result['chunks']} chunks)")


if __name__ == "__main__":
    main()
