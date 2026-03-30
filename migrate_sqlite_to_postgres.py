from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
from dotenv import load_dotenv


def _parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _bool(value) -> bool:
    return bool(int(value)) if value is not None and str(value).strip() != "" else False


async def _apply_schema(conn: asyncpg.Connection) -> None:
    schema_sql = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    await conn.execute(schema_sql)


async def migrate(sqlite_path: Path, database_url: str) -> None:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = await asyncpg.connect(database_url)
    await _apply_schema(pg_conn)

    counters = {
        "users": 0,
        "submissions": 0,
        "giveaway_participants": 0,
        "giveaway_meta": 0,
    }

    try:
        async with pg_conn.transaction():
            for row in sqlite_conn.execute("SELECT * FROM users ORDER BY id ASC"):
                await pg_conn.execute(
                    """
                    INSERT INTO users (
                        id, telegram_id, username, first_name, last_name, created_at, last_seen,
                        is_subscribed, is_admin, is_blocked, is_active, submissions_count
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                    ON CONFLICT (telegram_id) DO UPDATE
                    SET username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        created_at = COALESCE(users.created_at, EXCLUDED.created_at),
                        last_seen = EXCLUDED.last_seen,
                        is_subscribed = EXCLUDED.is_subscribed,
                        is_admin = EXCLUDED.is_admin,
                        is_blocked = EXCLUDED.is_blocked,
                        is_active = EXCLUDED.is_active,
                        submissions_count = EXCLUDED.submissions_count
                    """,
                    row["id"],
                    row["telegram_id"],
                    row["username"] or "",
                    row["first_name"] or "",
                    row["last_name"] or "",
                    _parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
                    _parse_datetime(row["last_seen"]) or _parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
                    _bool(row["is_subscribed"]),
                    _bool(row["is_admin"]),
                    _bool(row["is_blocked"]),
                    _bool(row["is_active"]) if row["is_active"] is not None else True,
                    int(row["submissions_count"] or 0),
                )
                counters["users"] += 1

            for row in sqlite_conn.execute("SELECT * FROM submissions ORDER BY id ASC"):
                await pg_conn.execute(
                    """
                    INSERT INTO submissions (
                        id, user_id, username, first_name, original_text, final_text, signature, base_signature,
                        anonymous, base_anonymous, is_admin_signature, file_id, media_type, status, moderator_id,
                        created_at, scheduled_at, published_at, scheduled_by,
                        source_chat_id, source_message_id, card_chat_id, card_message_id
                    )
                    VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,
                        $9,$10,$11,$12,$13,$14,$15,
                        $16,$17,$18,$19,
                        $20,$21,$22,$23
                    )
                    ON CONFLICT (id) DO UPDATE
                    SET user_id = EXCLUDED.user_id,
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        original_text = EXCLUDED.original_text,
                        final_text = EXCLUDED.final_text,
                        signature = EXCLUDED.signature,
                        base_signature = EXCLUDED.base_signature,
                        anonymous = EXCLUDED.anonymous,
                        base_anonymous = EXCLUDED.base_anonymous,
                        is_admin_signature = EXCLUDED.is_admin_signature,
                        file_id = EXCLUDED.file_id,
                        media_type = EXCLUDED.media_type,
                        status = EXCLUDED.status,
                        moderator_id = EXCLUDED.moderator_id,
                        created_at = EXCLUDED.created_at,
                        scheduled_at = EXCLUDED.scheduled_at,
                        published_at = EXCLUDED.published_at,
                        scheduled_by = EXCLUDED.scheduled_by,
                        source_chat_id = EXCLUDED.source_chat_id,
                        source_message_id = EXCLUDED.source_message_id,
                        card_chat_id = EXCLUDED.card_chat_id,
                        card_message_id = EXCLUDED.card_message_id
                    """,
                    row["id"],
                    row["user_id"],
                    row["username"] or "",
                    row["first_name"] or "",
                    row["original_text"] or "",
                    row["final_text"] or "",
                    row["signature"] or "",
                    row["base_signature"] or "",
                    _bool(row["anonymous"]),
                    _bool(row["base_anonymous"]),
                    _bool(row["is_admin_signature"]),
                    row["file_id"] or "",
                    (row["media_type"] if "media_type" in row.keys() else "") or "",
                    row["status"] or "pending",
                    row["moderator_id"],
                    _parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
                    _parse_datetime(row["scheduled_at"]),
                    _parse_datetime(row["published_at"]),
                    row["scheduled_by"],
                    row["source_chat_id"],
                    row["source_message_id"],
                    row["card_chat_id"],
                    row["card_message_id"],
                )
                counters["submissions"] += 1

            for row in sqlite_conn.execute("SELECT * FROM giveaway_participants ORDER BY id ASC"):
                await pg_conn.execute(
                    """
                    INSERT INTO giveaway_participants (
                        id, telegram_id, username, first_name, joined_at, is_winner
                    )
                    VALUES ($1,$2,$3,$4,$5,$6)
                    ON CONFLICT (telegram_id) DO UPDATE
                    SET username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        joined_at = EXCLUDED.joined_at,
                        is_winner = EXCLUDED.is_winner
                    """,
                    row["id"],
                    row["telegram_id"],
                    row["username"] or "",
                    row["first_name"] or "",
                    _parse_datetime(row["joined_at"]) or datetime.now(timezone.utc),
                    _bool(row["is_winner"]),
                )
                counters["giveaway_participants"] += 1

            for row in sqlite_conn.execute("SELECT * FROM giveaway_meta"):
                await pg_conn.execute(
                    """
                    INSERT INTO giveaway_meta (key, value)
                    VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                    """,
                    row["key"],
                    row["value"],
                )
                counters["giveaway_meta"] += 1

            await pg_conn.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence('users', 'id'),
                    COALESCE((SELECT MAX(id) FROM users), 1),
                    (SELECT COUNT(*) > 0 FROM users)
                )
                """
            )
            await pg_conn.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence('submissions', 'id'),
                    COALESCE((SELECT MAX(id) FROM submissions), 1),
                    (SELECT COUNT(*) > 0 FROM submissions)
                )
                """
            )
            await pg_conn.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence('giveaway_participants', 'id'),
                    COALESCE((SELECT MAX(id) FROM giveaway_participants), 1),
                    (SELECT COUNT(*) > 0 FROM giveaway_participants)
                )
                """
            )
    finally:
        sqlite_conn.close()
        await pg_conn.close()

    print("Migration completed")
    print(f"users: {counters['users']}")
    print(f"submissions: {counters['submissions']}")
    print(f"giveaway_participants: {counters['giveaway_participants']}")
    print(f"giveaway_meta: {counters['giveaway_meta']}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Migrate SQLite bot.db to PostgreSQL")
    parser.add_argument("--sqlite-path", default="bot.db", help="Path to SQLite database file")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is required in .env")

    asyncio.run(migrate(Path(args.sqlite_path), database_url))


if __name__ == "__main__":
    main()
