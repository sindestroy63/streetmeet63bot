CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username TEXT NOT NULL DEFAULT '',
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_subscribed BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    submissions_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS submissions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL DEFAULT '',
    first_name TEXT NOT NULL DEFAULT '',
    original_text TEXT NOT NULL DEFAULT '',
    final_text TEXT NOT NULL DEFAULT '',
    signature TEXT NOT NULL DEFAULT '',
    base_signature TEXT NOT NULL DEFAULT '',
    anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    base_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin_signature BOOLEAN NOT NULL DEFAULT FALSE,
    file_id TEXT NOT NULL DEFAULT '',
    media_type TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    moderator_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    scheduled_by BIGINT,
    source_chat_id BIGINT,
    source_message_id BIGINT,
    card_chat_id BIGINT,
    card_message_id BIGINT
);

ALTER TABLE submissions
    ADD COLUMN IF NOT EXISTS media_type TEXT NOT NULL DEFAULT '';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'submissions_status_check'
    ) THEN
        ALTER TABLE submissions
            ADD CONSTRAINT submissions_status_check
            CHECK (status IN ('pending', 'scheduled', 'publishing', 'published', 'rejected'));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS giveaway_participants (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username TEXT NOT NULL DEFAULT '',
    first_name TEXT NOT NULL DEFAULT '',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_winner BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS giveaway_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active, is_blocked);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions (status);
CREATE INDEX IF NOT EXISTS idx_submissions_scheduled_at ON submissions (scheduled_at);
CREATE INDEX IF NOT EXISTS idx_submissions_user_id ON submissions (user_id);
CREATE INDEX IF NOT EXISTS idx_giveaway_is_winner ON giveaway_participants (is_winner);
