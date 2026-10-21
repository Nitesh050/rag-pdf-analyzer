# RAG Platform

Chat with your own documents, fully local. Upload a PDF (or index a web page), ask questions, and get answers grounded in that document with page citations. Everything runs on your machine: models are served by [Ollama](https://ollama.com), nothing is sent to a cloud API.

```
React (Vite) ──► FastAPI ──► Ollama
                   │           qwen2.5:7b        answers
                   │           nomic-embed-text  embeddings
                   │
     ┌─────────────┴──────────────┐
  Ingestion                     Question answering
  PDF  → Docling (layout + OCR)  question type → retrieval → prompt → answer
  URL  → BeautifulSoup           • page questions fetch the named pages
  → clean → chunk → embed        • summaries use per-section summaries
  → ChromaDB + BM25 index        • otherwise hybrid search (semantic + BM25, RRF)
```

## Features

- **PDF ingestion** with [Docling](https://github.com/docling-project/docling): keeps headings and tables, and OCRs text inside images (Apple Vision on macOS, RapidOCR elsewhere).
- **Web page ingestion** from a URL.
- **Hybrid retrieval**: semantic search in ChromaDB fused with BM25 keyword search (stemming, stopwords) via Reciprocal Rank Fusion. Optional cross-encoder reranking.
- **Grounded answers**: the model answers only from the document, cites `(Source N, page P)`, says what is missing when an answer is partial, and says "I couldn't find the answer…" instead of guessing. Only cited pages are shown as sources.
- **Page questions** ("what is on page 42?", "summarize pages 10–12") fetch those pages directly.
- **Summaries of long documents** via per-section summaries, cached per document and precomputed in the background after upload.
- **Re-indexing**: each chunk records the ingestion version; documents indexed by an older pipeline are re-processed on re-upload or with one command.
- **Evals** for retrieval and answer quality, with a calibrated LLM judge (see [Evaluation](#evaluation)).

## Requirements

- **Python 3.14** (used in development) for the API
- **Node.js 22** for the frontend
- **Ollama** with these models:
  ```
  ollama pull qwen2.5:7b          # answers
  ollama pull nomic-embed-text    # embeddings
  ollama pull llama3              # only for the generation eval's judge
  ```
- About 8 GB of free RAM for the 7B model

## Getting started

**1. API** (from `apps/api`)
```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```
Check it with `curl localhost:8000/health`. Interactive API docs are at http://localhost:8000/docs.

**2. Frontend** (from `apps/web`)
```
npm install
npm run dev
```
Open the URL Vite prints (http://localhost:5173 by default), log in with anything (authentication is not implemented yet), upload a PDF and start asking questions.

The first upload downloads Docling's layout models, so it is slower than later ones.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `CHROMA_DIR` | `data/chroma_db` | Where the vector index is stored |
| `SUMMARY_DIR` | `data/summaries` | Where per-section document summaries are cached |
| `PDF_OCR` | `true` | Set to `false` to skip OCR (faster uploads, but text inside images is lost) |
| `RERANKER_MODEL` | unset | e.g. `BAAI/bge-reranker-base` to enable cross-encoder reranking (better ranking, ~0.7 s slower per question on CPU) |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | API address used by the frontend |

Paths are relative to `apps/api`.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/upload` | multipart `file` (PDF) | `document_id`, chunk count |
| `POST` | `/upload/url` | `{"url": "https://..."}` | `document_id`, chunk count |
| `POST` | `/chat` | `{"question": "...", "document_id": "..."}` | `answer`, `sources` (page + file) |
| `GET` | `/health` | | `{"status": "ok"}` |

Pass the `document_id` returned by an upload to `/chat` to answer from that document only; without it, every uploaded document is searched.

## Project layout

```
apps/
  api/
    src/
      ingestion/    PDF and web adapters, text normalisation, chunking, re-indexing
      retrieval/    ChromaDB store, BM25, hybrid search, fusion, reranker
      generation/   RAG chain, prompt, question-type routing, page refs, summaries
      routers/      FastAPI endpoints
    evals/          golden set, retrieval and generation evals, LLM judge
    tests/          unit and integration tests
  web/              React + Vite frontend
infra/              docker-compose files (not written yet)
```

## Maintenance

**Re-index documents after changing the ingestion pipeline.** Bump `INGESTION_VERSION` in `src/ingestion/pipeline.py`, then from `apps/api`:
```
.venv/bin/python -m src.ingestion.reindex --dry-run   # list stale documents
.venv/bin/python -m src.ingestion.reindex             # re-process them
```
Documents keep their `document_id`. Restart the API afterwards so its in-memory keyword index is rebuilt.

**Run the tests** from `apps/api`:
```
.venv/bin/python -m pytest tests/unit          # fast, no models needed for most
.venv/bin/python -m pytest tests/integration   # needs Ollama running
```
Tests never touch your real index: they point `CHROMA_DIR` at a temporary folder.

## Evaluation

Changes to retrieval, chunking or the prompt are measured, not guessed. `apps/api/evals/` holds a golden set of 64 questions over three PDFs (a 223-page book, a slide deck and a code-heavy assignment), including page questions, summaries and questions the documents cannot answer.

```
.venv/bin/python -m evals.run_retrieval --name <run>    # is the right page retrieved?
.venv/bin/python -m evals.run_generation --name <run>   # is the answer right, cited, and honest?
```

Current results with `qwen2.5:7b`:

| | |
|---|---|
| Right page in top 5 (hybrid search) | 0.939 |
| Answer correctness (LLM judge) | 0.911 |
| Unanswerable questions answered "not found" | 6 / 8 |
| Citations pointing to the right source | 100% |

The judge is checked against human grades (92% agreement). See [`apps/api/evals/README.md`](apps/api/evals/README.md) for how the evals work, the judge calibration and run-to-run noise. The eval PDFs and run results are kept out of git.

## Status

Working: ingestion, retrieval, grounded answers, page questions, summaries, evals.

Not built yet:
- Docker setup for the API and `docker-compose`
- Database, user accounts and real login (the login page is a placeholder)
- Chat history and follow-up questions
- Listing, switching and deleting documents in the UI
- Background job queue for uploads and streaming answers
- CI

Known limitations:
- Diagrams: OCR reads the text in an image but not the drawing itself, so questions about a diagram's layout can be answered wrongly.
- Building summaries of a long book takes several minutes once per document (done in the background after upload).
- With the 7B model, answers take about 8 s. `qwen2.5:14b` scored higher in the evals (0.955 correctness) but takes about 13 s.
