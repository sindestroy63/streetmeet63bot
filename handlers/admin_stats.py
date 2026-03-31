from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

from config import Settings
from database import Database
from keyboards.admin_menu import ADMIN_STATS_BUTTON, ADMIN_USERS_BUTTON
from services.stats_service import get_full_stats, get_users_overview


router = Router(name="admin_stats")
_database: Database | None = None
_settings: Settings | None = None


def get_router(database: Database | None = None, settings: Settings | None = None) -> Router:
    global _database, _settings
    if database is not None:
        _database = database
    if settings is not None:
        _settings = settings
    return router


def _is_admin(message: Message) -> bool:
    return bool(_settings and message.from_user and _settings.is_admin(message.from_user.id))


@router.message(StateFilter(None), F.text == ADMIN_USERS_BUTTON)
async def show_users_stats(message: Message) -> None:
    if not _is_admin(message) or _database is None:
        return

    users = await get_users_overview(_database)
    await message.answer(
        "<b>Пользователи бота</b>\n\n"
        f"<b>Всего:</b> {users['total']}\n"
        f"<b>Активных:</b> {users['active']}\n"
        f"<b>Заблокировали бота:</b> {users['blocked']}"
    )


@router.message(StateFilter(None), F.text == ADMIN_STATS_BUTTON)
async def show_bot_stats(message: Message) -> None:
    if not _is_admin(message) or _database is None:
        return

    stats = await get_full_stats(_database)
    users = stats["users"]
    submissions = stats["submissions"]
    giveaway = stats["giveaway"]

    await message.answer(
        "<b>📊 Статистика бота</b>\n\n"
        f"<b>Пользователи:</b> {users['total']}\n"
        f"<b>Новых сегодня:</b> {users['today']}\n"
        f"<b>Всего предложек:</b> {submissions['total']}\n"
        f"<b>На модерации:</b> {submissions['pending']}\n"
        f"<b>Запланировано:</b> {submissions['scheduled']}\n"
        f"<b>Опубликовано:</b> {submissions['published']}\n"
        f"<b>Отклонено:</b> {submissions['rejected']}\n"
        f"<b>Предложек сегодня:</b> {submissions['today']}\n"
        f"<b>Участников розыгрыша:</b> {giveaway['total']}\n"
        f"<b>Победителей розыгрыша:</b> {giveaway['winners']}"
    )
