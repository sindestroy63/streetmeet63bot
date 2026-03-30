CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_subscribed INTEGER NOT NULL DEFAULT 0,
    is_admin INTEGER NOT NULL DEFAULT 0,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    submissions_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    first_name TEXT,
    original_text TEXT,
    final_text TEXT,
    signature TEXT,
    base_signature TEXT,
    is_admin_signature INTEGER NOT NULL DEFAULT 0,
    base_admin_signature INTEGER NOT NULL DEFAULT 0,
    anonymous INTEGER NOT NULL DEFAULT 0,
    base_anonymous INTEGER NOT NULL DEFAULT 0,
    file_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    moderator_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scheduled_at TEXT,
    scheduled_by INTEGER,
    published_at TEXT,
    source_chat_id INTEGER,
    source_message_id INTEGER,
    card_chat_id INTEGER,
    card_message_id INTEGER
);

CREATE TABLE IF NOT EXISTS giveaway_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    first_name TEXT,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_winner INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS giveaway_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
