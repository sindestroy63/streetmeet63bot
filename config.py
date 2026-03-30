from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


def _parse_admin_ids(raw_value: str) -> list[int]:
    return [int(part.strip()) for part in raw_value.split(",") if part.strip()]


def _parse_channel_id(raw_value: str) -> int | str:
    value = (raw_value or "").strip()
    if not value:
        return ""
    if value.lstrip("-").isdigit():
        return int(value)
    return value


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    admin_chat_id: int
    channel_id: int | str
    channel_url: str
    database_url: str
    database_path: str
    submission_cooldown_seconds: int
    timezone_name: str
    timezone: ZoneInfo
    giveaway_channel_1_url: str
    giveaway_channel_2_url: str
    giveaway_draw_at: datetime | None
    giveaway_winners_count: int

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


def load_settings() -> Settings:
    load_dotenv()

    database_url = (
        os.getenv("DATABASE_URL", "").strip()
        or os.getenv("DATABASE_PATH", "").strip()
    )
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    if not database_url.startswith(("postgresql://", "postgres://")):
        raise ValueError("DATABASE_URL must point to PostgreSQL")

    timezone_name = os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow"
    tz = ZoneInfo(timezone_name)

    draw_raw = os.getenv("GIVEAWAY_DRAW_AT", "").strip()
    giveaway_draw_at = None
    if draw_raw:
        giveaway_draw_at = datetime.strptime(draw_raw, "%Y-%m-%d %H:%M").replace(tzinfo=tz)

    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        admin_chat_id=int(os.getenv("ADMIN_CHAT_ID", "0").strip() or 0),
        channel_id=_parse_channel_id(os.getenv("CHANNEL_ID", "")),
        channel_url=os.getenv("CHANNEL_URL", "").strip(),
        database_url=database_url,
        database_path=database_url,
        submission_cooldown_seconds=int(os.getenv("SUBMISSION_COOLDOWN_SECONDS", "180").strip() or 180),
        timezone_name=timezone_name,
        timezone=tz,
        giveaway_channel_1_url=os.getenv("GIVEAWAY_CHANNEL_1_URL", "").strip(),
        giveaway_channel_2_url=os.getenv("GIVEAWAY_CHANNEL_2_URL", "").strip(),
        giveaway_draw_at=giveaway_draw_at,
        giveaway_winners_count=int(os.getenv("GIVEAWAY_WINNERS_COUNT", "5").strip() or 5),
    )
