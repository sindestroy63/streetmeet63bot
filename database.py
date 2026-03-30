from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass(slots=True)
class BotUser:
    id: int
    telegram_id: int
    username: str
    first_name: str
    last_name: str
    created_at: datetime
    last_seen: datetime
    is_subscribed: bool = False
    is_admin: bool = False
    is_blocked: bool = False
    is_active: bool = True
    submissions_count: int = 0


@dataclass(slots=True)
class SuggestedPost:
    id: int
    user_id: int
    username: str
    first_name: str
    original_text: str
    final_text: str
    signature: str
    base_signature: str
    anonymous: bool
    base_anonymous: bool
    is_admin_signature: bool
    file_id: str
    media_type: str
    status: str
    moderator_id: int | None
    created_at: datetime
    scheduled_at: datetime | None
    published_at: datetime | None
    scheduled_by: int | None
    source_chat_id: int | None
    source_message_id: int | None
    card_chat_id: int | None
    card_message_id: int | None

    @property
    def moderation_chat_id(self) -> int | None:
        return self.card_chat_id

    @property
    def moderation_message_id(self) -> int | None:
        return self.card_message_id

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


@dataclass(slots=True)
class GiveawayParticipant:
    id: int
    telegram_id: int
    username: str
    first_name: str
    joined_at: datetime
    is_winner: bool = False


class Database:
    def __init__(self, dsn: str | Path) -> None:
        self.dsn = str(dsn)
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def init(self) -> None:
        if self._pool is None:
            await self.connect()
        await self._apply_schema()

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return self._pool

    async def _apply_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        sql = schema_path.read_text(encoding="utf-8")
        async with self._require_pool().acquire() as conn:
            await conn.execute(sql)

    def _row_to_user(self, row: asyncpg.Record | None) -> BotUser | None:
        if row is None:
            return None
        return BotUser(**dict(row))

    def _row_to_post(self, row: asyncpg.Record | None) -> SuggestedPost | None:
        if row is None:
            return None
        return SuggestedPost(**dict(row))

    def _row_to_participant(self, row: asyncpg.Record | None) -> GiveawayParticipant | None:
        if row is None:
            return None
        return GiveawayParticipant(**dict(row))

    async def get_user_by_telegram_id(self, telegram_id: int) -> BotUser | None:
        async with self._require_pool().acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
        return self._row_to_user(row)

    async def upsert_user(
        self,
        telegram_id: int,
        username: str = "",
        first_name: str = "",
        last_name: str = "",
        *,
        is_admin: bool = False,
        is_subscribed: bool | None = None,
        current_time: str | datetime | None = None,
        **_kwargs,
    ) -> tuple[BotUser, bool]:
        now = _coerce_datetime(current_time) or _utc_now()
        async with self._require_pool().acquire() as conn:
            existed = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE telegram_id = $1)", telegram_id)
            row = await conn.fetchrow(
                """
                INSERT INTO users (
                    telegram_id, username, first_name, last_name,
                    created_at, last_seen, is_subscribed, is_admin,
                    is_blocked, is_active, submissions_count
                )
                VALUES ($1, $2, $3, $4, $5, $6, COALESCE($7, FALSE), $8, FALSE, TRUE, 0)
                ON CONFLICT (telegram_id) DO UPDATE
                SET username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    last_seen = EXCLUDED.last_seen,
                    is_admin = EXCLUDED.is_admin,
                    is_subscribed = COALESCE($7, users.is_subscribed)
                RETURNING *
                """,
                telegram_id,
                username or "",
                first_name or "",
                last_name or "",
                now,
                now,
                is_subscribed,
                bool(is_admin),
            )
        return self._row_to_user(row), not bool(existed)

    async def update_user_subscription(self, telegram_id: int, is_subscribed: bool) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_subscribed = $1, last_seen = $2 WHERE telegram_id = $3",
                bool(is_subscribed),
                _utc_now(),
                telegram_id,
            )

    async def update_user_activity(self, telegram_id: int) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_seen = $1, is_active = TRUE WHERE telegram_id = $2",
                _utc_now(),
                telegram_id,
            )

    async def mark_user_blocked(self, telegram_id: int) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_blocked = TRUE, is_active = FALSE WHERE telegram_id = $1",
                telegram_id,
            )

    async def increment_user_submissions(self, telegram_id: int) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "UPDATE users SET submissions_count = submissions_count + 1 WHERE telegram_id = $1",
                telegram_id,
            )

    async def get_all_users(self) -> list[BotUser]:
        async with self._require_pool().acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users ORDER BY id ASC")
        return [self._row_to_user(row) for row in rows]

    async def get_active_user_ids(self) -> list[int]:
        async with self._require_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT telegram_id FROM users WHERE is_blocked = FALSE AND is_active = TRUE ORDER BY id ASC"
            )
        return [row["telegram_id"] for row in rows]

    async def get_total_users_count(self) -> int:
        async with self._require_pool().acquire() as conn:
            value = await conn.fetchval("SELECT COUNT(*) FROM users")
        return int(value or 0)

    async def get_user_stats(self) -> dict[str, int]:
        async with self._require_pool().acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN is_blocked = FALSE AND is_active = TRUE THEN 1 ELSE 0 END) AS active,
                    SUM(CASE WHEN is_blocked = TRUE THEN 1 ELSE 0 END) AS blocked,
                    SUM(CASE WHEN created_at >= date_trunc('day', NOW()) THEN 1 ELSE 0 END) AS today
                FROM users
                """
            )
        return {
            "total": int(row["total"] or 0),
            "active": int(row["active"] or 0),
            "blocked": int(row["blocked"] or 0),
            "today": int(row["today"] or 0),
        }

    async def get_user_counts(self) -> dict[str, int]:
        return await self.get_user_stats()

    async def create_submission(
        self,
        *,
        user_id: int,
        username: str = "",
        first_name: str = "",
        original_text: str = "",
        final_text: str | None = None,
        signature: str = "",
        base_signature: str = "",
        anonymous: bool = False,
        base_anonymous: bool = False,
        is_admin_signature: bool = False,
        file_id: str = "",
        media_type: str = "",
        status: str = "pending",
        moderator_id: int | None = None,
        created_at: str | datetime | None = None,
        scheduled_at: str | datetime | None = None,
        published_at: str | datetime | None = None,
        scheduled_by: int | None = None,
        source_chat_id: int | None = None,
        source_message_id: int | None = None,
        card_chat_id: int | None = None,
        card_message_id: int | None = None,
        **_kwargs,
    ) -> SuggestedPost:
        async with self._require_pool().acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO submissions (
                    user_id, username, first_name, original_text, final_text, signature,
                    base_signature, anonymous, base_anonymous, is_admin_signature, file_id, media_type,
                    status, moderator_id, created_at, scheduled_at, published_at, scheduled_by,
                    source_chat_id, source_message_id, card_chat_id, card_message_id
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10, $11, $12,
                    $13, $14, $15, $16, $17, $18,
                    $19, $20, $21, $22
                )
                RETURNING *
                """,
                user_id,
                username or "",
                first_name or "",
                original_text or "",
                final_text if final_text is not None else (original_text or ""),
                signature or "",
                base_signature or "",
                bool(anonymous),
                bool(base_anonymous),
                bool(is_admin_signature),
                file_id or "",
                media_type or "",
                status,
                moderator_id,
                _coerce_datetime(created_at) or _utc_now(),
                _coerce_datetime(scheduled_at),
                _coerce_datetime(published_at),
                scheduled_by,
                source_chat_id,
                source_message_id,
                card_chat_id,
                card_message_id,
            )
        return self._row_to_post(row)

    async def create_post(self, **kwargs) -> int:
        post = await self.create_submission(**kwargs)
        return post.id

    async def get_last_submission_created_at(self, user_id: int) -> str | None:
        async with self._require_pool().acquire() as conn:
            value = await conn.fetchval(
                "SELECT created_at FROM submissions WHERE user_id = $1 ORDER BY id DESC LIMIT 1",
                user_id,
            )
        if value is None:
            return None
        return _coerce_datetime(value).isoformat()

    async def get_submission(self, post_id: int) -> SuggestedPost | None:
        async with self._require_pool().acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM submissions WHERE id = $1", int(post_id))
        return self._row_to_post(row)

    async def get_post(self, post_id: Any) -> SuggestedPost | None:
        if isinstance(post_id, SuggestedPost):
            return await self.get_submission(post_id.id)
        return await self.get_submission(int(post_id))

    async def set_admin_messages(self, post_id: int, **kwargs) -> None:
        source_chat_id = kwargs.get("source_chat_id", kwargs.get("content_chat_id"))
        source_message_id = kwargs.get("source_message_id", kwargs.get("content_message_id"))
        card_chat_id = kwargs.get("card_chat_id", kwargs.get("admin_card_chat_id", kwargs.get("moderation_chat_id")))
        card_message_id = kwargs.get(
            "card_message_id",
            kwargs.get("admin_card_message_id", kwargs.get("moderation_message_id")),
        )
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                """
                UPDATE submissions
                SET source_chat_id = COALESCE($1, source_chat_id),
                    source_message_id = COALESCE($2, source_message_id),
                    card_chat_id = COALESCE($3, card_chat_id),
                    card_message_id = COALESCE($4, card_message_id)
                WHERE id = $5
                """,
                source_chat_id,
                source_message_id,
                card_chat_id,
                card_message_id,
                post_id,
            )

    async def update_final_text(self, post_id: int, final_text: str) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute("UPDATE submissions SET final_text = $1 WHERE id = $2", final_text or "", post_id)

    async def update_signature(self, post_id: int, signature: str) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute("UPDATE submissions SET signature = $1 WHERE id = $2", signature or "", post_id)

    async def set_admin_signature(self, post_id: int, is_admin_signature: bool) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "UPDATE submissions SET is_admin_signature = $1 WHERE id = $2",
                bool(is_admin_signature),
                post_id,
            )

    async def set_anonymous(self, post_id: int, anonymous: bool) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute("UPDATE submissions SET anonymous = $1 WHERE id = $2", bool(anonymous), post_id)

    async def reset_post(self, post_id: int) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                """
                UPDATE submissions
                SET final_text = original_text,
                    signature = base_signature,
                    anonymous = base_anonymous,
                    is_admin_signature = FALSE
                WHERE id = $1
                """,
                post_id,
            )

    async def reject_post(self, post_id: int, moderator_id: int | None = None) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "UPDATE submissions SET status = 'rejected', moderator_id = $1 WHERE id = $2",
                moderator_id,
                post_id,
            )

    async def schedule_post(self, post_id: int, scheduled_at: str | datetime, scheduled_by: int | None = None) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                """
                UPDATE submissions
                SET status = 'scheduled',
                    scheduled_at = $1,
                    scheduled_by = $2,
                    moderator_id = COALESCE($2, moderator_id)
                WHERE id = $3
                """,
                _coerce_datetime(scheduled_at),
                scheduled_by,
                post_id,
            )

    async def unschedule_post(self, post_id: int) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                "UPDATE submissions SET status = 'pending', scheduled_at = NULL, scheduled_by = NULL WHERE id = $1",
                post_id,
            )

    async def get_due_scheduled_posts(self, now_iso: str | datetime) -> list[SuggestedPost]:
        async with self._require_pool().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM submissions
                WHERE status = 'scheduled'
                  AND scheduled_at IS NOT NULL
                  AND scheduled_at <= $1
                ORDER BY scheduled_at ASC, id ASC
                """,
                _coerce_datetime(now_iso) or _utc_now(),
            )
        return [self._row_to_post(row) for row in rows]

    async def claim_scheduled_post(self, post_id: int) -> bool:
        async with self._require_pool().acquire() as conn:
            result = await conn.execute(
                "UPDATE submissions SET status = 'pending' WHERE id = $1 AND status = 'scheduled'",
                post_id,
            )
        return result.endswith("1")

    async def start_publication(self, post_id: int) -> bool:
        async with self._require_pool().acquire() as conn:
            result = await conn.execute(
                "UPDATE submissions SET status = 'publishing' WHERE id = $1 AND status IN ('pending', 'scheduled')",
                post_id,
            )
        return result.endswith("1")

    async def rollback_publication(self, post_id: int, previous_status: str = "pending") -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute("UPDATE submissions SET status = $1 WHERE id = $2", previous_status, post_id)

    async def finish_publication(self, post_id: int, moderator_id: int | None = None) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                """
                UPDATE submissions
                SET status = 'published',
                    published_at = $1,
                    moderator_id = COALESCE($2, moderator_id)
                WHERE id = $3
                """,
                _utc_now(),
                moderator_id,
                post_id,
            )

    async def get_submission_stats(self) -> dict[str, int]:
        async with self._require_pool().acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN status = 'scheduled' THEN 1 ELSE 0 END) AS scheduled,
                    SUM(CASE WHEN status = 'publishing' THEN 1 ELSE 0 END) AS publishing,
                    SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) AS published,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                    SUM(CASE WHEN created_at >= date_trunc('day', NOW()) THEN 1 ELSE 0 END) AS today
                FROM submissions
                """
            )
        return {
            "total": int(row["total"] or 0),
            "pending": int(row["pending"] or 0),
            "scheduled": int(row["scheduled"] or 0),
            "publishing": int(row["publishing"] or 0),
            "published": int(row["published"] or 0),
            "rejected": int(row["rejected"] or 0),
            "today": int(row["today"] or 0),
        }

    async def get_submission_counts(self) -> dict[str, int]:
        return await self.get_submission_stats()

    async def get_giveaway_participant(self, telegram_id: int) -> GiveawayParticipant | None:
        async with self._require_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM giveaway_participants WHERE telegram_id = $1",
                telegram_id,
            )
        return self._row_to_participant(row)

    async def upsert_giveaway_participant(
        self,
        telegram_id: int,
        username: str = "",
        first_name: str = "",
    ) -> tuple[GiveawayParticipant, bool]:
        async with self._require_pool().acquire() as conn:
            existed = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM giveaway_participants WHERE telegram_id = $1)",
                telegram_id,
            )
            row = await conn.fetchrow(
                """
                INSERT INTO giveaway_participants (telegram_id, username, first_name, joined_at, is_winner)
                VALUES ($1, $2, $3, $4, FALSE)
                ON CONFLICT (telegram_id) DO UPDATE
                SET username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name
                RETURNING *
                """,
                telegram_id,
                username or "",
                first_name or "",
                _utc_now(),
            )
        return self._row_to_participant(row), not bool(existed)

    async def get_all_giveaway_participants(self) -> list[GiveawayParticipant]:
        async with self._require_pool().acquire() as conn:
            rows = await conn.fetch("SELECT * FROM giveaway_participants ORDER BY id ASC")
        return [self._row_to_participant(row) for row in rows]

    async def get_giveaway_participants_count(self) -> int:
        async with self._require_pool().acquire() as conn:
            value = await conn.fetchval("SELECT COUNT(*) FROM giveaway_participants")
        return int(value or 0)

    async def set_giveaway_winners(self, telegram_ids: list[int]) -> None:
        async with self._require_pool().acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE giveaway_participants SET is_winner = FALSE")
                if telegram_ids:
                    await conn.execute(
                        "UPDATE giveaway_participants SET is_winner = TRUE WHERE telegram_id = ANY($1::bigint[])",
                        telegram_ids,
                    )

    async def get_giveaway_winners(self) -> list[GiveawayParticipant]:
        async with self._require_pool().acquire() as conn:
            rows = await conn.fetch("SELECT * FROM giveaway_participants WHERE is_winner = TRUE ORDER BY id ASC")
        return [self._row_to_participant(row) for row in rows]

    async def get_meta_value(self, key: str) -> str | None:
        async with self._require_pool().acquire() as conn:
            return await conn.fetchval("SELECT value FROM giveaway_meta WHERE key = $1", key)

    async def set_meta_value(self, key: str, value: str) -> None:
        async with self._require_pool().acquire() as conn:
            await conn.execute(
                """
                INSERT INTO giveaway_meta (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                key,
                value,
            )

    async def is_giveaway_draw_completed(self) -> bool:
        return (await self.get_meta_value("giveaway_draw_completed")) == "1"

    async def mark_giveaway_draw_completed(self) -> None:
        await self.set_meta_value("giveaway_draw_completed", "1")

    async def get_giveaway_stats(self) -> dict[str, int]:
        async with self._require_pool().acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN is_winner = TRUE THEN 1 ELSE 0 END) AS winners
                FROM giveaway_participants
                """
            )
        return {
            "total": int(row["total"] or 0),
            "winners": int(row["winners"] or 0),
        }
