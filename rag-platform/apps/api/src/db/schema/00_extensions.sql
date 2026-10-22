-- Extensions and helpers shared by every table.

CREATE EXTENSION IF NOT EXISTS citext;     -- case-insensitive text (emails)
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector: embeddings + similarity search (replaces Chroma)

-- Keeps updated_at current on every UPDATE. Attached with a trigger to
-- each table that has an updated_at column.
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
