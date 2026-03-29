from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiosqlite


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


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
    anonymous: bool
    base_anonymous: bool
    file_id: str | None
    status: str
    moderator_id: int | None
    created_at: str
    scheduled_at: str | None
    scheduled_by: int | None
    published_at: str | None
    admin_content_message_id: int | None
    admin_card_message_id: int | None


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if self._connection is not None:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA foreign_keys = ON;")
        await self._connection.commit()

    async def init(self) -> None:
        await self.connect()
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        await self._connection.executescript(schema_sql)
        await self._ensure_column("users", "is_subscribed", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("users", "is_admin", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("users", "is_blocked", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("users", "is_active", "INTEGER NOT NULL DEFAULT 1")
        await self._ensure_column("users", "submissions_count", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("suggested_posts", "base_signature", "TEXT")
        await self._ensure_column("suggested_posts", "base_anonymous", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("suggested_posts", "scheduled_at", "TEXT")
        await self._ensure_column("suggested_posts", "scheduled_by", "INTEGER")
        await self._connection.commit()

    async def close(self) -> None:
        if self._connection is None:
            return
        await self._connection.close()
        self._connection = None

    async def upsert_user(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        is_admin: bool,
        current_time: str,
    ) -> tuple[BotUser, bool]:
        existing = await self.get_user_by_telegram_id(telegram_id)
        if existing is None:
            cursor = await self._connection.execute(
                """
                INSERT INTO users (
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    created_at,
                    last_seen,
                    is_admin
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    current_time,
                    current_time,
                    int(is_admin),
                ),
            )
            await self._connection.commit()
            user = await self.get_user_by_id(int(cursor.lastrowid))
            if user is None:
                raise RuntimeError("Newly created user could not be loaded from database.")
            return user, True

        await self._connection.execute(
            """
            UPDATE users
            SET username = ?,
                first_name = ?,
                last_name = ?,
                last_seen = ?,
                is_admin = ?,
                is_active = 1
            WHERE telegram_id = ?
            """,
            (username, first_name, last_name, current_time, int(is_admin), telegram_id),
        )
        await self._connection.commit()
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            raise RuntimeError("Existing user disappeared from database.")
        return user, False

    async def get_user_by_telegram_id(self, telegram_id: int) -> BotUser | None:
        cursor = await self._connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_user(row) if row else None

    async def get_user_by_id(self, user_id: int) -> BotUser | None:
        cursor = await self._connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_user(row) if row else None

    async def update_user_subscription(self, telegram_id: int, is_subscribed: bool) -> None:
        await self._connection.execute(
            """
            UPDATE users
            SET is_subscribed = ?, is_active = 1
            WHERE telegram_id = ?
            """,
            (int(is_subscribed), telegram_id),
        )
        await self._connection.commit()

    async def mark_user_blocked(self, telegram_id: int, is_blocked: bool) -> None:
        await self._connection.execute(
            """
            UPDATE users
            SET is_blocked = ?, is_active = ?
            WHERE telegram_id = ?
            """,
            (int(is_blocked), int(not is_blocked), telegram_id),
        )
        await self._connection.commit()

    async def increment_user_submissions(self, telegram_id: int) -> None:
        await self._connection.execute(
            """
            UPDATE users
            SET submissions_count = submissions_count + 1
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )
        await self._connection.commit()

    async def get_broadcast_users(self) -> list[BotUser]:
        cursor = await self._connection.execute(
            """
            SELECT *
            FROM users
            WHERE is_active = 1
            ORDER BY id ASC
            """
        )
        rows = await cursor.fetchall()
        return [self._row_to_user(row) for row in rows]

    async def get_user_counts(self) -> dict[str, int]:
        total = await self._fetch_int("SELECT COUNT(*) FROM users")
        active = await self._fetch_int(
            "SELECT COUNT(*) FROM users WHERE is_active = 1 AND is_blocked = 0"
        )
        blocked = await self._fetch_int("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
        today = await self._fetch_int(
            "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')"
        )
        return {
            "total": total,
            "active": active,
            "blocked": blocked,
            "today": today,
        }

    async def get_submission_counts(self) -> dict[str, int]:
        total = await self._fetch_int("SELECT COUNT(*) FROM suggested_posts")
        pending = await self._fetch_int(
            "SELECT COUNT(*) FROM suggested_posts WHERE status = 'pending'"
        )
        published = await self._fetch_int(
            "SELECT COUNT(*) FROM suggested_posts WHERE status = 'published'"
        )
        rejected = await self._fetch_int(
            "SELECT COUNT(*) FROM suggested_posts WHERE status = 'rejected'"
        )
        today = await self._fetch_int(
            "SELECT COUNT(*) FROM suggested_posts WHERE date(created_at) = date('now')"
        )
        return {
            "total": total,
            "pending": pending,
            "published": published,
            "rejected": rejected,
            "today": today,
        }

    async def get_last_submission_created_at(self, user_id: int) -> str | None:
        cursor = await self._connection.execute(
            """
            SELECT created_at
            FROM suggested_posts
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        return row["created_at"] if row else None

    async def create_post(
        self,
        *,
        user_id: int,
        username: str | None,
        first_name: str | None,
        original_text: str | None,
        final_text: str | None,
        signature: str | None,
        base_signature: str | None,
        anonymous: bool,
        base_anonymous: bool,
        file_id: str | None,
        created_at: str,
    ) -> int:
        cursor = await self._connection.execute(
            """
            INSERT INTO suggested_posts (
                user_id,
                username,
                first_name,
                original_text,
                final_text,
                signature,
                base_signature,
                anonymous,
                base_anonymous,
                file_id,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                first_name,
                original_text,
                final_text,
                signature,
                base_signature,
                int(anonymous),
                int(base_anonymous),
                file_id,
                created_at,
            ),
        )
        await self._connection.commit()
        return int(cursor.lastrowid)

    async def get_post(self, post_id: int) -> SuggestedPost | None:
        cursor = await self._connection.execute(
            "SELECT * FROM suggested_posts WHERE id = ?",
            (post_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_post(row) if row else None

    async def set_admin_messages(
        self,
        post_id: int,
        *,
        content_message_id: int,
        card_message_id: int,
    ) -> None:
        await self._connection.execute(
            """
            UPDATE suggested_posts
            SET admin_content_message_id = ?, admin_card_message_id = ?
            WHERE id = ?
            """,
            (content_message_id, card_message_id, post_id),
        )
        await self._connection.commit()

    async def update_final_text(self, post_id: int, final_text: str | None) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET final_text = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (final_text, post_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def update_signature(self, post_id: int, signature: str | None) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET signature = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (signature, post_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def set_anonymous(self, post_id: int, anonymous: bool) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET anonymous = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (int(anonymous), post_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def reset_post(self, post_id: int) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET final_text = original_text,
                signature = base_signature,
                anonymous = base_anonymous
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (post_id,),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def schedule_post(self, post_id: int, scheduled_at: str, scheduled_by: int) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET status = 'scheduled',
                scheduled_at = ?,
                scheduled_by = ?,
                moderator_id = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (scheduled_at, scheduled_by, scheduled_by, post_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def unschedule_post(self, post_id: int) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET status = 'pending',
                scheduled_at = NULL,
                scheduled_by = NULL
            WHERE id = ? AND status = 'scheduled'
            """,
            (post_id,),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def get_due_scheduled_posts(self, now_iso: str, limit: int = 20) -> list[SuggestedPost]:
        cursor = await self._connection.execute(
            """
            SELECT *
            FROM suggested_posts
            WHERE status = 'scheduled'
              AND scheduled_at IS NOT NULL
              AND scheduled_at <= ?
            ORDER BY scheduled_at ASC, id ASC
            LIMIT ?
            """,
            (now_iso, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_post(row) for row in rows]

    async def claim_scheduled_post(self, post_id: int) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET status = 'publishing'
            WHERE id = ? AND status = 'scheduled'
            """,
            (post_id,),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def start_publication(self, post_id: int, moderator_id: int) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET status = 'publishing', moderator_id = ?
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (moderator_id, post_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def finish_publication(self, post_id: int, published_at: str) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET status = 'published', published_at = ?
            WHERE id = ? AND status = 'publishing'
            """,
            (published_at, post_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def rollback_publication(self, post_id: int, restore_status: str) -> None:
        await self._connection.execute(
            """
            UPDATE suggested_posts
            SET status = ?, moderator_id = NULL
            WHERE id = ? AND status = 'publishing'
            """,
            (restore_status, post_id),
        )
        await self._connection.commit()

    async def mark_rejected(self, post_id: int, moderator_id: int) -> bool:
        cursor = await self._connection.execute(
            """
            UPDATE suggested_posts
            SET status = 'rejected', moderator_id = ?, scheduled_at = NULL, scheduled_by = NULL
            WHERE id = ? AND status IN ('pending', 'scheduled')
            """,
            (moderator_id, post_id),
        )
        await self._connection.commit()
        return cursor.rowcount > 0

    async def _fetch_int(self, query: str, parameters: tuple = ()) -> int:
        cursor = await self._connection.execute(query, parameters)
        row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def _ensure_column(self, table_name: str, column_name: str, column_sql: str) -> None:
        cursor = await self._connection.execute(f"PRAGMA table_info({table_name})")
        rows = await cursor.fetchall()
        existing_columns = {row["name"] for row in rows}
        if column_name in existing_columns:
            return
        await self._connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
        )

    @staticmethod
    def _row_to_user(row: aiosqlite.Row) -> BotUser:
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

    @staticmethod
    def _row_to_post(row: aiosqlite.Row) -> SuggestedPost:
        return SuggestedPost(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            first_name=row["first_name"],
            original_text=row["original_text"],
            final_text=row["final_text"],
            signature=row["signature"],
            base_signature=row["base_signature"],
            anonymous=bool(row["anonymous"]),
            base_anonymous=bool(row["base_anonymous"]),
            file_id=row["file_id"],
            status=row["status"],
            moderator_id=row["moderator_id"],
            created_at=row["created_at"],
            scheduled_at=row["scheduled_at"],
            scheduled_by=row["scheduled_by"],
            published_at=row["published_at"],
            admin_content_message_id=row["admin_content_message_id"],
            admin_card_message_id=row["admin_card_message_id"],
        )
