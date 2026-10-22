-- Uploaded sources, their chunks, background ingestion work and cached
-- section summaries.

CREATE TABLE documents (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),  -- = document_id in the vector store
    owner_id           uuid        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type        text        NOT NULL CHECK (source_type IN ('pdf', 'url', 'youtube')),
    title              text,                                -- e.g. extracted paper title
    filename           text,                                -- original upload name (pdf)
    source_url         text,                                -- url / youtube
    storage_path       text,                                -- where the file is kept (disk path or S3 key)
    content_hash       text        NOT NULL,                -- sha256 of the file bytes, or of the URL
    mime_type          text,
    size_bytes         bigint      CHECK (size_bytes >= 0),
    page_count         integer     CHECK (page_count >= 0),
    status             text        NOT NULL DEFAULT 'uploaded'
                       CHECK (status IN ('uploaded', 'processing', 'ready', 'failed')),
    error_message      text,
    ingestion_version  integer,                             -- INGESTION_VERSION it was indexed with
    chunk_count        integer     NOT NULL DEFAULT 0 CHECK (chunk_count >= 0),
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    indexed_at         timestamptz,
    deleted_at         timestamptz,                         -- soft delete; chunks are purged by a job
    CONSTRAINT documents_pdf_has_filename CHECK (source_type <> 'pdf' OR filename IS NOT NULL),
    CONSTRAINT documents_link_has_url     CHECK (source_type = 'pdf' OR source_url IS NOT NULL)
);

CREATE TRIGGER documents_set_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Duplicate uploads are detected per user. A global check would hand user B
-- the document_id of user A's copy of the same file.
CREATE UNIQUE INDEX documents_owner_hash_uniq
    ON documents (owner_id, content_hash) WHERE deleted_at IS NULL;

CREATE INDEX documents_owner_recent_idx
    ON documents (owner_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX documents_pending_idx
    ON documents (status) WHERE status IN ('uploaded', 'processing');


-- Chunk text, metadata and embedding: everything the vector store held.
-- Semantic search is a pgvector query on this table, so access control is a
-- join on documents.owner_id and deleting a document deletes its vectors in
-- the same transaction. The text also feeds the BM25 index and lets chunks
-- be re-embedded after a model change without re-parsing the PDF.
CREATE TABLE chunks (
    id                 text        PRIMARY KEY,             -- "{document_id}_{chunk_index}"
    document_id        uuid        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index        integer     NOT NULL CHECK (chunk_index >= 0),
    page               integer,
    start_char         integer,                             -- offset within the page
    text               text        NOT NULL,
    char_count         integer     NOT NULL,
    word_count         integer     NOT NULL,
    ingestion_version  integer     NOT NULL,
    -- NULL until the chunk is embedded. 768 = nomic-embed-text; a model with
    -- another size needs a migration and a re-embed.
    embedding          vector(768),
    embedding_model    text,                                -- e.g. nomic-embed-text
    created_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index),
    CONSTRAINT chunks_embedding_has_model CHECK (embedding IS NULL OR embedding_model IS NOT NULL)
);

CREATE INDEX chunks_reading_order_idx ON chunks (document_id, page, chunk_index);

-- Approximate nearest-neighbour index for semantic search across many
-- documents. Cosine distance (<=>) suits nomic-embed-text. Searches inside
-- one document touch only its few hundred chunks and are fast without it;
-- for filtered searches over the index, set hnsw.iterative_scan so the
-- filter can't leave too few results.
CREATE INDEX chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops);


-- Background work that outlives a request: ingest after upload, reindex
-- after an INGESTION_VERSION bump, precompute section summaries.
CREATE TABLE ingestion_jobs (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     uuid        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    kind            text        NOT NULL CHECK (kind IN ('ingest', 'reindex', 'summarize')),
    status          text        NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    attempts        integer     NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    settings        jsonb       NOT NULL DEFAULT '{}',      -- e.g. {"ocr": true, "model": "qwen2.5:14b"}
    error_message   text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    started_at      timestamptz,
    finished_at     timestamptz
);

CREATE INDEX ingestion_jobs_queue_idx
    ON ingestion_jobs (status, created_at) WHERE status IN ('queued', 'running');

CREATE INDEX ingestion_jobs_document_idx ON ingestion_jobs (document_id);


-- Map step of map-reduce summarisation (replaces data/summaries/*.json).
-- A row is valid only for the model, summariser version and ingestion
-- version that produced it.
CREATE TABLE section_summaries (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id        uuid        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_index      integer     NOT NULL CHECK (section_index >= 0),
    page_start         integer     NOT NULL,
    page_end           integer     NOT NULL,
    summary            text        NOT NULL,
    model              text        NOT NULL,                -- e.g. qwen2.5:14b
    summary_version    integer     NOT NULL,                -- DocumentSummarizer.VERSION
    ingestion_version  integer     NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT section_summaries_page_range CHECK (page_end >= page_start),
    UNIQUE (document_id, model, summary_version, ingestion_version, section_index)
);
