# Database schema

PostgreSQL schema for the RAG platform: users, documents and their embeddings (pgvector), background jobs, summaries and chat. The files run in numbered order.

| File | Tables |
|---|---|
| `00_extensions.sql` | `citext`, `pgcrypto`, `vector` (pgvector), `set_updated_at()` trigger function |
| `01_users.sql` | `users`, `sessions` |
| `02_documents.sql` | `documents`, `chunks`, `ingestion_jobs`, `section_summaries` |
| `03_chat.sql` | `conversations`, `messages`, `message_sources`, `feedback` |

```
users ──< sessions
  │
  ├──< documents ──< chunks
  │       ├──< ingestion_jobs
  │       └──< section_summaries
  │
  └──< conversations ──< messages ──< message_sources
                            └──< feedback
```

## Try it

Apply the schema to a throwaway Postgres with pgvector (Docker runs the files in order):

```
docker run --rm -d --name rag-db -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=rag \
  -v "$PWD/src/db/schema:/docker-entrypoint-initdb.d:ro" -p 5432:5432 pgvector/pgvector:pg16
docker exec -it rag-db psql -U postgres -d rag -c '\dt'
```

Run from `apps/api`. Stop it with `docker stop rag-db`. The plain `postgres` image won't work: it doesn't include the `vector` extension.

## Design notes

- **Embeddings live in `chunks.embedding` (pgvector), replacing Chroma.** Semantic search is a SQL query ordered by cosine distance (`embedding <=> :query`), so restricting it to a user's documents is a join and deleting a document removes its vectors in the same transaction. The column is `vector(768)` for nomic-embed-text; a model with a different size needs a migration and a re-embed. `embedding_model` records which model produced each vector.
- **Search index:** `chunks_embedding_hnsw_idx` (HNSW, cosine) speeds up search across many documents. Searching one document only touches its own few hundred chunks. When filtering on top of the index, enable `hnsw.iterative_scan` so the filter can't return too few rows.
- **Duplicate uploads are detected per user** (`documents_owner_hash_uniq`). The current app checks content hashes globally, which would give one user another user's document.
- **Documents are soft-deleted** (`deleted_at`) so old conversations can still reference them; a job purges their chunks and vectors.
- **Statuses and roles are `text` with `CHECK`**, not Postgres enums, so adding a value is a one-line migration.
- **`messages.standalone_question`** stores a follow-up rewritten for retrieval ("And a fruit fly?" -> "How many neurons does a fruit fly have?"), for conversation memory.
- **Eval data stays in `evals/`**, not in the database. Thumbs-down `feedback` is the source of new eval questions.

## Status

These files are the design, checked against Postgres 16: they apply cleanly, and constraints, triggers and cascades were tested (per-user dedup, re-upload after soft delete, rejected invalid values, `updated_at`, deleting a user removes their data).

Not done yet: SQLAlchemy models (`src/models/`), Alembic migrations (`src/db/migrations/`), the database session (`src/db/session.py`), Postgres in docker-compose, and switching the app from Chroma and JSON files to these tables (vector store, BM25 rebuild, summaries cache, eval harness).
