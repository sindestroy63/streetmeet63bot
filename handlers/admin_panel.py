from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import Settings
from database import Database
from keyboards.admin_menu import ADMIN_CLOSE_BUTTON, build_admin_menu
from keyboards.user_menu import ADMIN_PANEL_BUTTON, build_user_menu


router = Router(name="admin_panel")
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


@router.message(StateFilter(None), Command("admin"))
@router.message(StateFilter(None), F.text == ADMIN_PANEL_BUTTON)
async def open_admin_panel(message: Message) -> None:
    if not _is_admin(message):
        return
    await message.answer(
        "<b>⚙️ Админ-панель</b>\n\nВыбери действие ниже 👇",
        reply_markup=build_admin_menu(),
    )


@router.message(StateFilter(None), F.text == ADMIN_CLOSE_BUTTON)
async def close_admin_panel(message: Message) -> None:
    if not _is_admin(message):
        return
    await message.answer(
        "<b>Главное меню</b>\n\nВыбери действие ниже 👇",
        reply_markup=build_user_menu(is_admin=True),
    )
