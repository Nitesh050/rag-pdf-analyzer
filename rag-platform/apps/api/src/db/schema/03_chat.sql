-- Conversations, messages, the sources behind each answer, and feedback.

CREATE TABLE conversations (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id     uuid        REFERENCES documents(id) ON DELETE SET NULL,  -- active document
    title           text,                                   -- e.g. first question, trimmed
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    archived_at     timestamptz
);

CREATE TRIGGER conversations_set_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX conversations_user_recent_idx
    ON conversations (user_id, updated_at DESC) WHERE archived_at IS NULL;


CREATE TABLE messages (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     uuid        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role                text        NOT NULL CHECK (role IN ('user', 'assistant')),
    content             text        NOT NULL,

    -- Assistant messages only.
    standalone_question text,       -- follow-up rewritten for retrieval: "And a fruit fly?" -> "How many neurons does a fruit fly have?"
    intent              text        CHECK (intent IN ('qa', 'summary', 'explanation', 'comparison', 'chapter', 'metadata')),
    refused             boolean,    -- answered "I couldn't find the answer..."
    model               text,
    prompt_tokens       integer,
    completion_tokens   integer,
    latency_ms          integer,

    status              text        NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'error')),
    error_message       text,
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT messages_user_has_no_answer_fields
        CHECK (role = 'assistant' OR (intent IS NULL AND refused IS NULL AND model IS NULL))
);

CREATE INDEX messages_conversation_idx ON messages (conversation_id, created_at);


-- The context an answer was built from, in "Source N" order. cited = the
-- answer referenced it, so it was shown to the user as a source.
CREATE TABLE message_sources (
    message_id      uuid        NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    source_number   integer     NOT NULL CHECK (source_number >= 1),
    document_id     uuid        REFERENCES documents(id) ON DELETE SET NULL,
    chunk_id        text        REFERENCES chunks(id) ON DELETE SET NULL,
    page            integer,
    page_end        integer,    -- section summaries cover a page range
    cited           boolean     NOT NULL DEFAULT false,
    PRIMARY KEY (message_id, source_number)
);


-- Thumbs up / down on an answer. Every thumbs-down is a candidate question
-- for the eval golden set.
CREATE TABLE feedback (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id      uuid        NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id         uuid        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating          smallint    NOT NULL CHECK (rating IN (-1, 1)),
    comment         text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (message_id, user_id)
);
