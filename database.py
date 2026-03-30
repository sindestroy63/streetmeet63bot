from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite


@dataclass(slots=True)
class BotUser:
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    created_at: str
    last_seen: str
    is_subscribed: bool
    is_admin: bool
    is_blocked: bool
    is_active: bool
    submissions_count: int


@dataclass(slots=True)
class SuggestedPost:
    id: int
    user_id: int
    username: str | None
    first_name: str | None
    original_text: str | None
    final_text: str | None
    signature: str | None
    base_signature: str | None
    is_admin_signature: bool
    base_admin_signature: bool
    anonymous: bool
    base_anonymous: bool
    file_id: str | None
    status: str
    moderator_id: int | None
    created_at: str
    scheduled_at: str | None
    scheduled_by: int | None
    published_at: str | None
    source_chat_id: int | None
    source_message_id: int | None
    card_chat_id: int | None
    card_message_id: int | None

    @property
    def content_chat_id(self) -> int | None:
        return self.source_chat_id

    @property
    def content_message_id(self) -> int | None:
        return self.source_message_id

    @property
    def admin_card_chat_id(self) -> int | None:
        return self.card_chat_id

    @property
    def admin_card_message_id(self) -> int | None:
        return self.card_message_id

    @property
    def moderation_chat_id(self) -> int | None:
        return self.card_chat_id

    @property
    def moderation_message_id(self) -> int | None:
        return self.card_message_id


@dataclass(slots=True)
class GiveawayParticipant:
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    joined_at: str
    is_winner: bool


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path.as_posix())
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.execute("PRAGMA journal_mode = WAL")
        await self.connection.commit()

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()
            self.connection = None

    async def init(self) -> None:
        await self.connect()
        await self._create_tables()
        await self._run_migrations()

    def _conn(self) -> aiosqlite.Connection:
        if self.connection is None:
            raise RuntimeError("Database is not connected")
        return self.connection

    async def _create_tables(self) -> None:
        conn = self._conn()
        await conn.executescript(
            """
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
            """
        )
        await conn.commit()

    async def _run_migrations(self) -> None:
        await self._ensure_column("users", "last_name", "TEXT")
        await self._ensure_column("users", "created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
        await self._ensure_column("users", "last_seen", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
        await self._ensure_column("users", "is_subscribed", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("users", "is_admin", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("users", "is_blocked", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("users", "is_active", "INTEGER NOT NULL DEFAULT 1")
        await self._ensure_column("users", "submissions_count", "INTEGER NOT NULL DEFAULT 0")

        await self._ensure_column("submissions", "final_text", "TEXT")
        await self._ensure_column("submissions", "signature", "TEXT")
        await self._ensure_column("submissions", "base_signature", "TEXT")
        await self._ensure_column("submissions", "is_admin_signature", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("submissions", "base_admin_signature", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("submissions", "anonymous", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("submissions", "base_anonymous", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("submissions", "scheduled_at", "TEXT")
        await self._ensure_column("submissions", "scheduled_by", "INTEGER")
        await self._ensure_column("submissions", "published_at", "TEXT")
        await self._ensure_column("submissions", "source_chat_id", "INTEGER")
        await self._ensure_column("submissions", "source_message_id", "INTEGER")
        await self._ensure_column("submissions", "card_chat_id", "INTEGER")
        await self._ensure_column("submissions", "card_message_id", "INTEGER")
        await self._ensure_column("giveaway_participants", "username", "TEXT")
        await self._ensure_column("giveaway_participants", "first_name", "TEXT")
        await self._ensure_column("giveaway_participants", "joined_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
        await self._ensure_column("giveaway_participants", "is_winner", "INTEGER NOT NULL DEFAULT 0")

    async def _ensure_column(self, table: str, column: str, definition: str) -> None:
        conn = self._conn()
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        await cursor.close()
        existing = {row["name"] for row in rows}
        if column not in existing:
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            await conn.commit()

    def _user_from_row(self, row: aiosqlite.Row | None) -> BotUser | None:
        if row is None:
            return None
        return BotUser(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            created_at=row["created_at"],
            last_seen=row["last_seen"],
            is_subscribed=bool(row["is_subscribed"]),
            is_admin=bool(row["is_admin"]),
            is_blocked=bool(row["is_blocked"]),
            is_active=bool(row["is_active"]),
            submissions_count=row["submissions_count"],
        )

    def _post_from_row(self, row: aiosqlite.Row | None) -> SuggestedPost | None:
        if row is None:
            return None
        return SuggestedPost(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            first_name=row["first_name"],
            original_text=row["original_text"],
            final_text=row["final_text"],
            signature=row["signature"],
            base_signature=row["base_signature"],
            is_admin_signature=bool(row["is_admin_signature"]),
            base_admin_signature=bool(row["base_admin_signature"]),
            anonymous=bool(row["anonymous"]),
            base_anonymous=bool(row["base_anonymous"]),
            file_id=row["file_id"],
            status=row["status"],
            moderator_id=row["moderator_id"],
            created_at=row["created_at"],
            scheduled_at=row["scheduled_at"],
            scheduled_by=row["scheduled_by"],
            published_at=row["published_at"],
            source_chat_id=row["source_chat_id"],
            source_message_id=row["source_message_id"],
            card_chat_id=row["card_chat_id"],
            card_message_id=row["card_message_id"],
        )

    def _giveaway_participant_from_row(self, row: aiosqlite.Row | None) -> GiveawayParticipant | None:
        if row is None:
            return None
        return GiveawayParticipant(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_name=row["first_name"],
            joined_at=row["joined_at"],
            is_winner=bool(row["is_winner"]),
        )

    async def get_user_by_telegram_id(self, telegram_id: int) -> BotUser | None:
        conn = self._conn()
        cursor = await conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return self._user_from_row(row)

    async def upsert_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        is_admin: bool = False,
        is_subscribed: bool | None = None,
        current_time: str | None = None,
    ) -> tuple[BotUser, bool]:
        conn = self._conn()
        existing = await self.get_user_by_telegram_id(telegram_id)
        if existing is None:
            await conn.execute(
                """
                INSERT INTO users (
                    telegram_id, username, first_name, last_name, last_seen, is_admin, is_subscribed
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
                """,
                (
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    int(is_admin),
                    int(is_subscribed or False),
                ),
            )
            await conn.commit()
            user = await self.get_user_by_telegram_id(telegram_id)
            if user is None:
                raise RuntimeError("Failed to create user")
            return user, True

        await conn.execute(
            """
            UPDATE users
            SET username = ?,
                first_name = ?,
                last_name = ?,
                last_seen = CURRENT_TIMESTAMP,
                is_admin = ?,
                is_subscribed = COALESCE(?, is_subscribed),
                is_active = 1
            WHERE telegram_id = ?
            """,
            (
                username,
                first_name,
                last_name,
                int(is_admin),
                None if is_subscribed is None else int(is_subscribed),
                telegram_id,
            ),
        )
        await conn.commit()
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            raise RuntimeError("Failed to load updated user")
        return user, False

    async def update_user_subscription(self, telegram_id: int, is_subscribed: bool) -> None:
        conn = self._conn()
        await conn.execute(
            """
            UPDATE users
            SET is_subscribed = ?, last_seen = CURRENT_TIMESTAMP, is_active = 1
            WHERE telegram_id = ?
            """,
            (int(is_subscribed), telegram_id),
        )
        await conn.commit()

    async def update_user_activity(self, telegram_id: int) -> None:
        conn = self._conn()
        await conn.execute(
            "UPDATE users SET last_seen = CURRENT_TIMESTAMP, is_active = 1 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await conn.commit()

    async def mark_user_blocked(self, telegram_id: int, is_blocked: bool = True) -> None:
        conn = self._conn()
        await conn.execute(
            "UPDATE users SET is_blocked = ?, is_active = ? WHERE telegram_id = ?",
            (int(is_blocked), int(not is_blocked), telegram_id),
        )
        await conn.commit()

    async def increment_user_submissions(self, telegram_id: int) -> None:
        conn = self._conn()
        await conn.execute(
            """
            UPDATE users
            SET submissions_count = submissions_count + 1,
                last_seen = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )
        await conn.commit()

    async def get_all_users(self) -> list[BotUser]:
        conn = self._conn()
        cursor = await conn.execute("SELECT * FROM users ORDER BY id DESC")
        rows = await cursor.fetchall()
        await cursor.close()
        return [self._user_from_row(row) for row in rows if row is not None]

    async def get_active_user_ids(self) -> list[int]:
        conn = self._conn()
        cursor = await conn.execute(
            "SELECT telegram_id FROM users WHERE is_blocked = 0 AND is_active = 1 ORDER BY id ASC"
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [row["telegram_id"] for row in rows]

    async def create_submission(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        original_text: str | None,
        file_id: str | None,
        final_text: str | None = None,
        signature: str | None = None,
        base_signature: str | None = None,
        is_admin_signature: bool = False,
        base_admin_signature: bool | None = None,
        anonymous: bool = False,
        base_anonymous: bool | None = None,
        status: str = "pending",
    ) -> SuggestedPost:
        conn = self._conn()
        resolved_final_text = final_text if final_text is not None else original_text
        resolved_base_signature = base_signature if base_signature is not None else signature
        resolved_base_admin_signature = (
            is_admin_signature if base_admin_signature is None else base_admin_signature
        )
        resolved_base_anonymous = anonymous if base_anonymous is None else base_anonymous
        cursor = await conn.execute(
            """
            INSERT INTO submissions (
                user_id, username, first_name, original_text, final_text, signature,
                base_signature, is_admin_signature, base_admin_signature,
                anonymous, base_anonymous, file_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                first_name,
                original_text,
                resolved_final_text,
                signature,
                resolved_base_signature,
                int(is_admin_signature),
                int(resolved_base_admin_signature),
                int(anonymous),
                int(resolved_base_anonymous),
                file_id,
                status,
            ),
        )
        await conn.commit()
        post_id = cursor.lastrowid
        await cursor.close()
        await self.increment_user_submissions(user_id)
        post = await self.get_submission(post_id)
        if post is None:
            raise RuntimeError("Failed to create submission")
        return post

    async def create_post(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        original_text: str | None,
        file_id: str | None,
        final_text: str | None = None,
        signature: str | None = None,
        base_signature: str | None = None,
        is_admin_signature: bool = False,
        base_admin_signature: bool | None = None,
        anonymous: bool = False,
        base_anonymous: bool | None = None,
        status: str = "pending",
        **_kwargs,
    ) -> int:
        created = await self.create_submission(
            user_id=user_id,
            username=username,
            first_name=first_name,
            original_text=original_text,
            file_id=file_id,
            final_text=final_text,
            signature=signature,
            base_signature=base_signature,
            is_admin_signature=is_admin_signature,
            base_admin_signature=base_admin_signature,
            anonymous=anonymous,
            base_anonymous=base_anonymous,
            status=status,
        )
        return created.id

    async def get_last_submission_created_at(self, user_id: int) -> str | None:
        conn = self._conn()
        cursor = await conn.execute(
            """
            SELECT created_at
            FROM submissions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        raw_value = row["created_at"]
        if raw_value is None:
            return None

        if isinstance(raw_value, str):
            try:
                parsed = datetime.fromisoformat(raw_value)
            except ValueError:
                try:
                    parsed = datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return raw_value

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.isoformat()

        return str(raw_value)

    async def get_submission(self, post_id: int) -> SuggestedPost | None:
        conn = self._conn()
        cursor = await conn.execute(
            "SELECT * FROM submissions WHERE id = ?",
            (post_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return self._post_from_row(row)

    async def get_post(self, post_id: int | SuggestedPost) -> SuggestedPost | None:
        if isinstance(post_id, SuggestedPost):
            post_id = post_id.id
        return await self.get_submission(post_id)

    async def set_admin_messages(
        self,
        post_id: int,
        source_chat_id: int | None = None,
        source_message_id: int | None = None,
        card_chat_id: int | None = None,
        card_message_id: int | None = None,
        content_chat_id: int | None = None,
        content_message_id: int | None = None,
        admin_card_chat_id: int | None = None,
        admin_card_message_id: int | None = None,
        moderation_chat_id: int | None = None,
        moderation_message_id: int | None = None,
    ) -> None:
        conn = self._conn()
        resolved_source_chat_id = source_chat_id if source_chat_id is not None else content_chat_id
        resolved_source_message_id = (
            source_message_id if source_message_id is not None else content_message_id
        )
        resolved_card_chat_id = (
            card_chat_id
            if card_chat_id is not None
            else admin_card_chat_id
            if admin_card_chat_id is not None
            else moderation_chat_id
        )
        resolved_card_message_id = (
            card_message_id
            if card_message_id is not None
            else admin_card_message_id
            if admin_card_message_id is not None
            else moderation_message_id
        )
        await conn.execute(
            """
            UPDATE submissions
            SET source_chat_id = ?, source_message_id = ?, card_chat_id = ?, card_message_id = ?
            WHERE id = ?
            """,
            (
                resolved_source_chat_id,
                resolved_source_message_id,
                resolved_card_chat_id,
                resolved_card_message_id,
                post_id,
            ),
        )
        await conn.commit()

    async def update_final_text(self, post_id: int, final_text: str | None) -> None:
        conn = self._conn()
        await conn.execute(
            """
            UPDATE submissions
            SET final_text = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (final_text, post_id),
        )
        await conn.commit()

    async def update_signature(self, post_id: int, signature: str | None) -> None:
        conn = self._conn()
        await conn.execute(
            """
            UPDATE submissions
            SET signature = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (signature, post_id),
        )
        await conn.commit()

    async def set_admin_signature(self, post_id: int, is_admin_signature: bool) -> None:
        conn = self._conn()
        await conn.execute(
            """
            UPDATE submissions
            SET is_admin_signature = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (int(is_admin_signature), post_id),
        )
        await conn.commit()

    async def set_anonymous(self, post_id: int, anonymous: bool) -> None:
        conn = self._conn()
        await conn.execute(
            """
            UPDATE submissions
            SET anonymous = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (int(anonymous), post_id),
        )
        await conn.commit()

    async def reset_post(self, post_id: int) -> None:
        conn = self._conn()
        await conn.execute(
            """
            UPDATE submissions
            SET final_text = original_text,
                signature = base_signature,
                is_admin_signature = base_admin_signature,
                anonymous = base_anonymous
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (post_id,),
        )
        await conn.commit()

    async def reject_post(self, post_id: int, moderator_id: int) -> bool:
        conn = self._conn()
        cursor = await conn.execute(
            """
            UPDATE submissions
            SET status = 'rejected', moderator_id = ?, scheduled_at = NULL, scheduled_by = NULL
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (moderator_id, post_id),
        )
        await conn.commit()
        changed = cursor.rowcount > 0
        await cursor.close()
        return changed

    async def schedule_post(self, post_id: int, scheduled_at: str, scheduled_by: int) -> bool:
        conn = self._conn()
        cursor = await conn.execute(
            """
            UPDATE submissions
            SET status = 'scheduled',
                scheduled_at = ?,
                scheduled_by = ?,
                moderator_id = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (scheduled_at, scheduled_by, scheduled_by, post_id),
        )
        await conn.commit()
        changed = cursor.rowcount > 0
        await cursor.close()
        return changed

    async def unschedule_post(self, post_id: int) -> bool:
        conn = self._conn()
        cursor = await conn.execute(
            """
            UPDATE submissions
            SET status = 'pending',
                scheduled_at = NULL,
                scheduled_by = NULL
            WHERE id = ? AND status = 'scheduled'
            """,
            (post_id,),
        )
        await conn.commit()
        changed = cursor.rowcount > 0
        await cursor.close()
        return changed

    async def get_due_scheduled_posts(self, now_iso: str, limit: int = 20) -> list[SuggestedPost]:
        conn = self._conn()
        cursor = await conn.execute(
            """
            SELECT * FROM submissions
            WHERE status = 'scheduled'
              AND scheduled_at IS NOT NULL
              AND scheduled_at <= ?
            ORDER BY scheduled_at ASC, id ASC
            LIMIT ?
            """,
            (now_iso, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [self._post_from_row(row) for row in rows if row is not None]

    async def claim_scheduled_post(self, post_id: int) -> bool:
        conn = self._conn()
        cursor = await conn.execute(
            """
            UPDATE submissions
            SET status = 'publishing'
            WHERE id = ? AND status = 'scheduled'
            """,
            (post_id,),
        )
        await conn.commit()
        changed = cursor.rowcount > 0
        await cursor.close()
        return changed

    async def start_publication(self, post_id: int, moderator_id: int) -> bool:
        conn = self._conn()
        cursor = await conn.execute(
            """
            UPDATE submissions
            SET status = 'publishing',
                moderator_id = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (moderator_id, post_id),
        )
        await conn.commit()
        changed = cursor.rowcount > 0
        await cursor.close()
        return changed

    async def rollback_publication(self, post_id: int, restore_status: str) -> None:
        conn = self._conn()
        await conn.execute(
            "UPDATE submissions SET status = ? WHERE id = ?",
            (restore_status, post_id),
        )
        await conn.commit()

    async def finish_publication(self, post_id: int, published_at: str) -> None:
        conn = self._conn()
        await conn.execute(
            """
            UPDATE submissions
            SET status = 'published',
                published_at = ?,
                scheduled_at = COALESCE(scheduled_at, ?)
            WHERE id = ?
            """,
            (published_at, published_at, post_id),
        )
        await conn.commit()

    async def get_submission_stats(self) -> dict[str, Any]:
        conn = self._conn()
        cursor = await conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'scheduled' THEN 1 ELSE 0 END) AS scheduled,
                SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) AS published,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN DATE(created_at) = DATE('now', 'localtime') THEN 1 ELSE 0 END) AS today
            FROM submissions
            """
        )
        row = await cursor.fetchone()
        await cursor.close()
        return {
            "total": row["total"] or 0,
            "pending": row["pending"] or 0,
            "scheduled": row["scheduled"] or 0,
            "published": row["published"] or 0,
            "rejected": row["rejected"] or 0,
            "today": row["today"] or 0,
        }

    async def get_submission_counts(self) -> dict[str, Any]:
        return await self.get_submission_stats()

    async def get_user_stats(self) -> dict[str, Any]:
        conn = self._conn()
        cursor = await conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN is_blocked = 1 THEN 1 ELSE 0 END) AS blocked,
                SUM(CASE WHEN DATE(created_at) = DATE('now', 'localtime') THEN 1 ELSE 0 END) AS today
            FROM users
            """
        )
        row = await cursor.fetchone()
        await cursor.close()
        return {
            "total": row["total"] or 0,
            "active": row["active"] or 0,
            "blocked": row["blocked"] or 0,
            "today": row["today"] or 0,
        }

    async def get_user_counts(self) -> dict[str, Any]:
        return await self.get_user_stats()

    async def get_total_users_count(self) -> int:
        conn = self._conn()
        cursor = await conn.execute("SELECT COUNT(*) AS total FROM users")
        row = await cursor.fetchone()
        await cursor.close()
        return int(row["total"] or 0)

    async def get_giveaway_participant(self, telegram_id: int) -> GiveawayParticipant | None:
        conn = self._conn()
        cursor = await conn.execute(
            "SELECT * FROM giveaway_participants WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return self._giveaway_participant_from_row(row)

    async def upsert_giveaway_participant(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
    ) -> tuple[GiveawayParticipant, bool]:
        conn = self._conn()
        existing = await self.get_giveaway_participant(telegram_id)
        if existing is None:
            await conn.execute(
                """
                INSERT INTO giveaway_participants (telegram_id, username, first_name)
                VALUES (?, ?, ?)
                """,
                (telegram_id, username, first_name),
            )
            await conn.commit()
            created = await self.get_giveaway_participant(telegram_id)
            if created is None:
                raise RuntimeError("Failed to create giveaway participant")
            return created, True

        await conn.execute(
            """
            UPDATE giveaway_participants
            SET username = ?, first_name = ?
            WHERE telegram_id = ?
            """,
            (username, first_name, telegram_id),
        )
        await conn.commit()
        updated = await self.get_giveaway_participant(telegram_id)
        if updated is None:
            raise RuntimeError("Failed to update giveaway participant")
        return updated, False

    async def get_all_giveaway_participants(self) -> list[GiveawayParticipant]:
        conn = self._conn()
        cursor = await conn.execute(
            "SELECT * FROM giveaway_participants ORDER BY joined_at ASC, id ASC"
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [self._giveaway_participant_from_row(row) for row in rows if row is not None]

    async def get_giveaway_participants_count(self) -> int:
        conn = self._conn()
        cursor = await conn.execute("SELECT COUNT(*) AS total FROM giveaway_participants")
        row = await cursor.fetchone()
        await cursor.close()
        return int(row["total"] or 0)

    async def set_giveaway_winners(self, winner_ids: list[int]) -> None:
        conn = self._conn()
        await conn.execute("UPDATE giveaway_participants SET is_winner = 0")
        if winner_ids:
            placeholders = ",".join("?" for _ in winner_ids)
            await conn.execute(
                f"UPDATE giveaway_participants SET is_winner = 1 WHERE telegram_id IN ({placeholders})",
                tuple(winner_ids),
            )
        await conn.commit()

    async def get_giveaway_winners(self) -> list[GiveawayParticipant]:
        conn = self._conn()
        cursor = await conn.execute(
            "SELECT * FROM giveaway_participants WHERE is_winner = 1 ORDER BY id ASC"
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [self._giveaway_participant_from_row(row) for row in rows if row is not None]

    async def get_meta_value(self, key: str) -> str | None:
        conn = self._conn()
        cursor = await conn.execute("SELECT value FROM giveaway_meta WHERE key = ?", (key,))
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return row["value"]

    async def set_meta_value(self, key: str, value: str) -> None:
        conn = self._conn()
        await conn.execute(
            """
            INSERT INTO giveaway_meta (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await conn.commit()

    async def is_giveaway_draw_completed(self) -> bool:
        return (await self.get_meta_value("giveaway_draw_completed")) == "1"

    async def mark_giveaway_draw_completed(self) -> None:
        await self.set_meta_value("giveaway_draw_completed", "1")

    async def get_giveaway_stats(self) -> dict[str, Any]:
        conn = self._conn()
        cursor = await conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_winner = 1 THEN 1 ELSE 0 END) AS winners
            FROM giveaway_participants
            """
        )
        row = await cursor.fetchone()
        await cursor.close()
        return {
            "total": int(row["total"] or 0),
            "winners": int(row["winners"] or 0),
            "completed": await self.is_giveaway_draw_completed(),
        }
