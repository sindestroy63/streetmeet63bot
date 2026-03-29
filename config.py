from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _parse_int_list(raw_value: str) -> tuple[int, ...]:
    items = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not items:
        raise ValueError("ADMIN_IDS must contain at least one Telegram user id.")
    return tuple(int(item) for item in items)


@dataclass(slots=True, frozen=True)
class Settings:
    bot_token: str
    admin_ids: tuple[int, ...]
    admin_chat_id: int
    channel_id: int
    channel_url: str
    timezone_name: str
    timezone: ZoneInfo
    database_path: Path
    submission_cooldown_seconds: int

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
    admin_chat_id_raw = os.getenv("ADMIN_CHAT_ID", "").strip()
    channel_id_raw = os.getenv("CHANNEL_ID", "").strip()
    channel_url = os.getenv("CHANNEL_URL", "").strip()
    timezone_name = os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow"
    database_path_raw = os.getenv("DATABASE_PATH", "bot.db").strip()
    cooldown_raw = os.getenv("SUBMISSION_COOLDOWN_SECONDS", "180").strip()

    missing = [
        name
        for name, value in (
            ("BOT_TOKEN", bot_token),
            ("ADMIN_IDS", admin_ids_raw),
            ("ADMIN_CHAT_ID", admin_chat_id_raw),
            ("CHANNEL_ID", channel_id_raw),
            ("CHANNEL_URL", channel_url),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    database_path = Path(database_path_raw)
    if not database_path.is_absolute():
        database_path = BASE_DIR / database_path

    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            "Invalid TIMEZONE or missing timezone database. "
            f"Current value: {timezone_name}. "
            "Install dependencies from requirements.txt, including tzdata."
        ) from exc

    return Settings(
        bot_token=bot_token,
        admin_ids=_parse_int_list(admin_ids_raw),
        admin_chat_id=int(admin_chat_id_raw),
        channel_id=int(channel_id_raw),
        channel_url=channel_url,
        timezone_name=timezone_name,
        timezone=timezone,
        database_path=database_path,
        submission_cooldown_seconds=max(1, int(cooldown_raw)),
    )
