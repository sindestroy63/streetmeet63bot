from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


def _parse_admin_ids(raw_value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in raw_value.split(",") if item.strip())


def _normalize_channel_reference(raw_value: str) -> int | str:
    value = (raw_value or "").strip()
    if not value:
        raise ValueError("CHANNEL_ID is required")

    if value.startswith("https://t.me/") or value.startswith("http://t.me/"):
        value = value.split("t.me/", maxsplit=1)[1]

    value = value.strip("/")

    if value.startswith("@"):
        return value

    if value.lstrip("-").isdigit():
        return int(value)

    if value.replace("_", "").isalnum():
        return f"@{value}"

    raise ValueError(
        "CHANNEL_ID must be a Telegram channel id (-100...) or @username or t.me link"
    )


def _parse_draw_at(raw_value: str, tzinfo: ZoneInfo) -> datetime:
    value = (raw_value or "").strip()
    if not value:
        value = "2026-04-05 18:00"

    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
    return parsed.replace(tzinfo=tzinfo)


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_ids: tuple[int, ...]
    admin_chat_id: int
    channel_id: int | str
    channel_url: str
    database_path: str
    submission_cooldown_seconds: int
    timezone_name: str
    timezone: ZoneInfo
    giveaway_channel_1_url: str
    giveaway_channel_2_url: str
    giveaway_draw_at: datetime
    giveaway_winners_count: int

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is required")

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

    admin_chat_id_raw = os.getenv("ADMIN_CHAT_ID", "").strip()
    if not admin_chat_id_raw:
        raise ValueError("ADMIN_CHAT_ID is required")

    channel_raw = os.getenv("CHANNEL_ID", "").strip()
    channel_url = os.getenv("CHANNEL_URL", "").strip()

    if not channel_raw and not channel_url:
        raise ValueError("CHANNEL_ID is required")

    timezone_name = os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow"

    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(
            f"Unknown timezone '{timezone_name}'. Install tzdata and use a valid IANA timezone."
        ) from error

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        admin_chat_id=int(admin_chat_id_raw),
        channel_id=_normalize_channel_reference(channel_raw or channel_url),
        channel_url=channel_url,
        database_path=os.getenv("DATABASE_PATH", "bot.db").strip() or "bot.db",
        submission_cooldown_seconds=int(
            os.getenv("SUBMISSION_COOLDOWN_SECONDS", "180").strip() or "180"
        ),
        timezone_name=timezone_name,
        timezone=timezone,
        giveaway_channel_1_url=os.getenv(
            "GIVEAWAY_CHANNEL_1_URL", "https://t.me/streetmeet63"
        ).strip(),
        giveaway_channel_2_url=os.getenv(
            "GIVEAWAY_CHANNEL_2_URL", "https://t.me/priora613"
        ).strip(),
        giveaway_draw_at=_parse_draw_at(
            os.getenv("GIVEAWAY_DRAW_AT", "2026-04-05 18:00"),
            timezone,
        ),
        giveaway_winners_count=int(os.getenv("GIVEAWAY_WINNERS_COUNT", "5").strip() or "5"),
    )
