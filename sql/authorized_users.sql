CREATE TABLE IF NOT EXISTS bot_test.authorized_users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    external_user_id TEXT NOT NULL,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT authorized_users_source_external_user_id_key UNIQUE (source, external_user_id)
);

CREATE INDEX IF NOT EXISTS ix_authorized_users_source_active
    ON bot_test.authorized_users (source, is_active);

-- Fill the allowlist manually after applying this script.
-- Example:
-- INSERT INTO bot_test.authorized_users (source, external_user_id, display_name, role, comment)
-- VALUES ('max', '123456789', 'Ivan Ivanov', 'user', 'MAX access');
