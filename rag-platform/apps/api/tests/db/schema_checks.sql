-- Behaviour checks for src/db/schema. Run against a fresh database with the
-- schema applied (see tests/db/README.md). Every line printed should start
-- with "ok"; anything starting with "FAIL" is a regression.
-- Runs in a transaction that is rolled back, so it leaves no data behind.

BEGIN;

CREATE FUNCTION pg_temp.expect_error(stmt text, label text) RETURNS text AS $$
BEGIN
    EXECUTE stmt;
    RETURN 'FAIL  ' || label || ' (was accepted)';
EXCEPTION WHEN others THEN
    RETURN 'ok    ' || label;
END;
$$ LANGUAGE plpgsql;

-- 768-d one-hot vector with a 1 at position i: a stand-in for a real embedding
CREATE FUNCTION pg_temp.onehot(i int) RETURNS vector AS $$
    SELECT array_agg(CASE WHEN g = i THEN 1 ELSE 0 END ORDER BY g)::vector
    FROM generate_series(1, 768) g;
$$ LANGUAGE sql;

INSERT INTO users (id, email, password_hash) VALUES
  ('00000000-0000-0000-0000-00000000000a', 'Alice@Example.com', 'h'),
  ('00000000-0000-0000-0000-00000000000b', 'bob@example.com', 'h');
INSERT INTO documents (id, owner_id, source_type, filename, content_hash) VALUES
  ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-00000000000a', 'pdf', 'book.pdf', 'hash1');

-- Users
SELECT pg_temp.expect_error($$INSERT INTO users (email, password_hash) VALUES ('alice@example.COM', 'h')$$, 'email unique, case-insensitive');

-- Documents
SELECT pg_temp.expect_error($$INSERT INTO documents (owner_id, source_type, filename, content_hash) VALUES ('00000000-0000-0000-0000-00000000000a','pdf','copy.pdf','hash1')$$, 'same user, same file rejected');
INSERT INTO documents (id, owner_id, source_type, filename, content_hash) VALUES ('00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-00000000000b','pdf','book.pdf','hash1');
SELECT 'ok    different user, same file allowed';
SELECT pg_temp.expect_error($$INSERT INTO documents (owner_id, source_type, content_hash) VALUES ('00000000-0000-0000-0000-00000000000a','pdf','h2')$$, 'pdf without filename');
SELECT pg_temp.expect_error($$INSERT INTO documents (owner_id, source_type, content_hash) VALUES ('00000000-0000-0000-0000-00000000000a','url','h3')$$, 'url without source_url');
SELECT pg_temp.expect_error($$UPDATE documents SET status = 'done' WHERE id = '00000000-0000-0000-0000-0000000000d1'$$, 'unknown status');
SELECT pg_temp.expect_error($$INSERT INTO section_summaries (document_id, section_index, page_start, page_end, summary, model, summary_version, ingestion_version) VALUES ('00000000-0000-0000-0000-0000000000d1',0,10,5,'s','m',1,1)$$, 'page_end before page_start');

-- updated_at is a transaction timestamp here, so compare against a value set explicitly
UPDATE documents SET updated_at = '2000-01-01' WHERE id = '00000000-0000-0000-0000-0000000000d1';
SELECT CASE WHEN updated_at > '2000-01-01' THEN 'ok    updated_at set by trigger' ELSE 'FAIL  updated_at trigger' END
FROM documents WHERE id = '00000000-0000-0000-0000-0000000000d1';

-- Chunks and embeddings (pgvector)
INSERT INTO chunks (id, document_id, chunk_index, page, text, char_count, word_count, ingestion_version, embedding, embedding_model)
SELECT 'd1_' || i, '00000000-0000-0000-0000-0000000000d1', i, i + 1, 'chunk ' || i, 7, 2, 2, pg_temp.onehot(i + 1), 'nomic-embed-text'
FROM generate_series(0, 4) i;
INSERT INTO chunks (id, document_id, chunk_index, page, text, char_count, word_count, ingestion_version, embedding, embedding_model)
VALUES ('d2_0', '00000000-0000-0000-0000-0000000000d2', 0, 1, 'bob chunk', 9, 2, 2, pg_temp.onehot(3), 'nomic-embed-text');

SELECT CASE WHEN (SELECT id FROM chunks ORDER BY embedding <=> pg_temp.onehot(3) LIMIT 1) IN ('d1_2', 'd2_0')
       THEN 'ok    nearest chunk found by cosine distance' ELSE 'FAIL  nearest-neighbour search' END;

SELECT CASE WHEN (
    SELECT array_agg(c.id ORDER BY c.embedding <=> pg_temp.onehot(3))
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE d.owner_id = '00000000-0000-0000-0000-00000000000b'
) = ARRAY['d2_0'] THEN 'ok    search restricted to one user''s documents by a join'
  ELSE 'FAIL  per-user search' END;

SELECT pg_temp.expect_error($$INSERT INTO chunks (id, document_id, chunk_index, text, char_count, word_count, ingestion_version, embedding, embedding_model) VALUES ('bad1','00000000-0000-0000-0000-0000000000d1',10,'t',1,1,2,'[1,2,3]','m')$$, 'embedding with wrong dimensions');
SELECT pg_temp.expect_error($$INSERT INTO chunks (id, document_id, chunk_index, text, char_count, word_count, ingestion_version, embedding) VALUES ('bad2','00000000-0000-0000-0000-0000000000d1',11,'t',1,1,2, pg_temp.onehot(1))$$, 'embedding without embedding_model');
INSERT INTO chunks (id, document_id, chunk_index, text, char_count, word_count, ingestion_version) VALUES ('d1_pending','00000000-0000-0000-0000-0000000000d1',12,'t',1,1,2);
SELECT 'ok    chunk without embedding allowed (embedded later)';

DELETE FROM documents WHERE id = '00000000-0000-0000-0000-0000000000d2';
SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM chunks WHERE document_id = '00000000-0000-0000-0000-0000000000d2')
       THEN 'ok    deleting a document deletes its vectors' ELSE 'FAIL  vectors left behind' END;

-- Soft delete and re-upload
UPDATE documents SET deleted_at = now() WHERE id = '00000000-0000-0000-0000-0000000000d1';
INSERT INTO documents (owner_id, source_type, filename, content_hash) VALUES ('00000000-0000-0000-0000-00000000000a','pdf','book.pdf','hash1');
SELECT 'ok    re-upload allowed after soft delete';

-- Chat
INSERT INTO conversations (id, user_id, document_id) VALUES ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-00000000000a','00000000-0000-0000-0000-0000000000d1');
INSERT INTO messages (id, conversation_id, role, content) VALUES ('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-0000000000c1','user','q');
SELECT pg_temp.expect_error($$INSERT INTO messages (conversation_id, role, content, intent) VALUES ('00000000-0000-0000-0000-0000000000c1','user','q','qa')$$, 'user message with assistant-only fields');
SELECT pg_temp.expect_error($$INSERT INTO messages (conversation_id, role, content, intent) VALUES ('00000000-0000-0000-0000-0000000000c1','assistant','a','guess')$$, 'unknown intent');
INSERT INTO message_sources (message_id, source_number, document_id, chunk_id, page, cited) VALUES ('00000000-0000-0000-0000-0000000000e1',1,'00000000-0000-0000-0000-0000000000d1','d1_0',1,true);
INSERT INTO feedback (message_id, user_id, rating) VALUES ('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-00000000000a',1);
SELECT pg_temp.expect_error($$INSERT INTO feedback (message_id, user_id, rating) VALUES ('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-00000000000a',-1)$$, 'one vote per user per answer');
SELECT pg_temp.expect_error($$INSERT INTO feedback (message_id, user_id, rating) VALUES ('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-00000000000b',5)$$, 'rating must be -1 or 1');

-- Deleting a user removes everything they own
DELETE FROM users WHERE email = 'alice@example.com';
SELECT CASE WHEN (SELECT count(*) FROM documents) + (SELECT count(*) FROM chunks)
               + (SELECT count(*) FROM conversations) + (SELECT count(*) FROM messages) = 0
       THEN 'ok    deleting a user cascades to documents, chunks, conversations, messages'
       ELSE 'FAIL  user delete left rows behind' END;

ROLLBACK;
