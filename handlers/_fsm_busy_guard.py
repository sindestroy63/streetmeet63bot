from __future__ import annotations

from aiogram.types import Message

from keyboards.admin_menu import (
    ADMIN_BROADCAST_BUTTON,
    ADMIN_CLOSE_BUTTON,
    ADMIN_GIVEAWAY_BUTTON,
    ADMIN_PANEL_BUTTON,
    ADMIN_STATS_BUTTON,
    ADMIN_USERS_BUTTON,
)
from keyboards.user_menu import GIVEAWAY_BUTTON, HOW_IT_WORKS_BUTTON


BUSY_SCENARIO_TEXT = "Сначала завершите текущий сценарий или нажмите Отмена"

TOP_LEVEL_COMMANDS = (
    "/admin",
    "/broadcast",
    "/giveaway",
    "/giveaway_admin",
)

USER_TOP_LEVEL_TEXTS = {
    HOW_IT_WORKS_BUTTON,
    GIVEAWAY_BUTTON,
    ADMIN_PANEL_BUTTON,
}

ADMIN_TOP_LEVEL_TEXTS = {
    ADMIN_PANEL_BUTTON,
    ADMIN_CLOSE_BUTTON,
    ADMIN_USERS_BUTTON,
    ADMIN_STATS_BUTTON,
    ADMIN_GIVEAWAY_BUTTON,
    ADMIN_BROADCAST_BUTTON,
}


def _normalized_text(text: str | None) -> str:
    return (text or "").strip()


def is_top_level_command_text(text: str | None) -> bool:
    normalized = _normalized_text(text).lower()
    return any(normalized == command or normalized.startswith(f"{command} ") for command in TOP_LEVEL_COMMANDS)


def is_user_top_level_text(text: str | None) -> bool:
    return _normalized_text(text) in USER_TOP_LEVEL_TEXTS


def is_admin_top_level_text(text: str | None) -> bool:
    return _normalized_text(text) in ADMIN_TOP_LEVEL_TEXTS


async def answer_busy_scenario(message: Message) -> None:
    await message.answer(BUSY_SCENARIO_TEXT)
