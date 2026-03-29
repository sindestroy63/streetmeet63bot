from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import Settings
from keyboards.admin_menu import (
    ADMIN_CLOSE_BUTTON,
    ADMIN_PANEL_BUTTON,
    build_admin_menu_keyboard,
)
from keyboards.user_menu import build_user_menu_keyboard
from utils.permissions import can_use_admin_messages
from utils.texts import ADMIN_PANEL_TEXT, MAIN_MENU_TEXT


def get_router(settings: Settings) -> Router:
    router = Router(name="admin_panel")

    @router.message(StateFilter("*"), Command("admin"))
    @router.message(StateFilter("*"), F.text == ADMIN_PANEL_BUTTON)
    async def open_admin_panel(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await state.clear()
        await message.answer(ADMIN_PANEL_TEXT, reply_markup=build_admin_menu_keyboard())

    @router.message(StateFilter("*"), F.text == ADMIN_CLOSE_BUTTON)
    async def close_admin_panel(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await state.clear()
        await message.answer(
            MAIN_MENU_TEXT,
            reply_markup=build_user_menu_keyboard(is_admin=True),
        )

    return router
