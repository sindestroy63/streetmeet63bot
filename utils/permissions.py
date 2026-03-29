from __future__ import annotations

from aiogram.types import CallbackQuery, Message, User

from config import Settings


def is_admin_id(user_id: int | None, settings: Settings) -> bool:
    return bool(user_id and settings.is_admin(user_id))


def is_admin_user(user: User | None, settings: Settings) -> bool:
    return bool(user and settings.is_admin(user.id))


def can_use_admin_callbacks(callback: CallbackQuery, settings: Settings) -> bool:
    return is_admin_user(callback.from_user, settings)


def can_use_admin_messages(message: Message, settings: Settings) -> bool:
    return is_admin_user(message.from_user, settings)
