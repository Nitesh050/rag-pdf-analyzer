"""
Shared plumbing for the eval scripts: loading the corpus and golden set,
caching Docling conversions, and building an isolated index.

Nothing here touches the app's real Chroma store (data/chroma_db).
Everything is written under evals/.cache/.
"""

import hashlib
import json
import os
import shutil
from importlib.metadata import version
from pathlib import Path

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

EVALS_CACHE = Path(__file__).resolve().parent / ".cache"
# Section summaries for summary questions are cached here, not in the
# app's data/summaries.
os.environ["SUMMARY_DIR"] = str(EVALS_CACHE / "summaries")

from langchain_core.documents import Document

from src.ingestion.chunking.chunker import DocumentChunker
from src.ingestion.pdf_adapter import PDFAdapter
from src.retrieval.retrieval_manager import RetrievalManager
from src.retrieval.vector_store import VectorStore

EVALS_DIR = Path(__file__).resolve().parent
CORPUS_DIR = EVALS_DIR / "corpus"
CACHE_DIR = EVALS_DIR / ".cache"
RESULTS_DIR = EVALS_DIR / "results"


def load_corpus() -> dict[str, dict]:
    manifest = json.loads((EVALS_DIR / "corpus.json").read_text())["documents"]

    for doc_key, entry in manifest.items():
        path = CORPUS_DIR / entry["file"]
        if not path.exists():
            raise FileNotFoundError(f"Missing corpus file for '{doc_key}': {path}")

        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise ValueError(
                f"{path.name} does not match corpus.json (sha256 {actual[:12]}...). "
                "Golden page numbers may no longer be valid."
            )
        entry["path"] = path

    return manifest


def load_golden(path: Path | None = None) -> list[dict]:
    path = path or EVALS_DIR / "golden.jsonl"
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("//")
    ]


class CachedPDFAdapter(PDFAdapter):
    """
    PDFAdapter that stores its per-page output on disk, keyed by file
    hash + Docling version + adapter options. Conversion is the slow
    step (minutes for a long book), so chunking/retrieval experiments
    re-run in seconds once the cache is warm.
    """

    def __init__(self, ocr: bool | None = None):
        # None follows the app's default (PDF_OCR), so evals measure what
        # production runs.
        super().__init__(ocr=ocr)

    def _convert(self, pdf_path: str | Path) -> list[Document]:
        # Only the raw Docling output is cached; PDFAdapter.load still
        # applies the current normalize_text() on top of it each run.
        pdf_path = Path(pdf_path)
        file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        key = hashlib.sha256(
            f"{file_hash}|docling={version('docling')}|ocr={self.ocr}".encode()
        ).hexdigest()[:16]

        cache_file = CACHE_DIR / "pages" / f"{pdf_path.stem}_{key}.json"

        if cache_file.exists():
            pages = json.loads(cache_file.read_text())
        else:
            pages = [
                {"page_content": d.page_content, "metadata": d.metadata}
                for d in super()._convert(pdf_path)
            ]
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(pages))

        return [Document(**page) for page in pages]


def chunk_corpus(corpus: dict[str, dict], ocr: bool | None = None) -> list[Document]:
    """
    Run each corpus PDF through the same adapter + chunker the app uses
    (mirrors IngestionPipeline.ingest_pdf), using the corpus key as
    document_id so results can be matched against golden doc names.
    """
    adapter = CachedPDFAdapter(ocr=ocr)
    chunker = DocumentChunker()

    chunks: list[Document] = []
    for doc_key, entry in corpus.items():
        doc_chunks = chunker.split(adapter.load(entry["path"]), document_id=doc_key)
        for chunk in doc_chunks:
            chunk.metadata["filename"] = entry["file"]
            # Match the app's relative "uploads/<file>" label. The absolute
            # corpus path is ~75 chars longer per chunk, which can push a
            # document over the prompt budget and onto a different path
            # (section summaries) than production takes.
            chunk.metadata["source"] = f"uploads/{entry['file']}"
        chunks.extend(doc_chunks)

    return chunks


def build_index(
    chunks: list[Document],
    reranker_model: str | None = None,
) -> RetrievalManager:
    """
    Embed chunks into an isolated Chroma directory and return a
    RetrievalManager over it. The directory is keyed by the chunk
    contents, so an unchanged chunking config reuses its embeddings.
    """
    fingerprint = hashlib.sha256()
    for chunk in chunks:
        fingerprint.update(chunk.page_content.encode())
        fingerprint.update(json.dumps(chunk.metadata, sort_keys=True, default=str).encode())
    index_dir = CACHE_DIR / "indexes" / fingerprint.hexdigest()[:16]

    complete_marker = index_dir / ".complete"
    if index_dir.exists() and not complete_marker.exists():
        # A previous run died mid-embedding; start over.
        shutil.rmtree(index_dir)

    vector_store = VectorStore(persist_directory=str(index_dir))

    if not complete_marker.exists():
        vector_store.add_documents(chunks)
        complete_marker.touch()

    manager = RetrievalManager(
        reranker_model=reranker_model,
        vector_store=vector_store,
    )
    manager.build_indexes()
    return manager
