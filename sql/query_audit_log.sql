CREATE TABLE IF NOT EXISTS bot_test.query_audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    external_user_id TEXT,
    role TEXT,
    query_text TEXT NOT NULL,
    parsed_query JSONB NOT NULL,
    decision_status TEXT NOT NULL,
    decision_message TEXT NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 0,
    top_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS query_audit_log_created_at_idx
    ON bot_test.query_audit_log (created_at DESC);
