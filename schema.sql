CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    is_subscribed INTEGER NOT NULL DEFAULT 0,
    is_admin INTEGER NOT NULL DEFAULT 0,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    submissions_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen);

CREATE TABLE IF NOT EXISTS suggested_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    first_name TEXT,
    original_text TEXT,
    final_text TEXT,
    signature TEXT,
    base_signature TEXT,
    anonymous INTEGER NOT NULL DEFAULT 0,
    base_anonymous INTEGER NOT NULL DEFAULT 0,
    file_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    moderator_id INTEGER,
    created_at TEXT NOT NULL,
    scheduled_at TEXT,
    scheduled_by INTEGER,
    published_at TEXT,
    admin_content_message_id INTEGER,
    admin_card_message_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_suggested_posts_user_id ON suggested_posts(user_id);
CREATE INDEX IF NOT EXISTS idx_suggested_posts_status ON suggested_posts(status);
CREATE INDEX IF NOT EXISTS idx_suggested_posts_created_at ON suggested_posts(created_at);
