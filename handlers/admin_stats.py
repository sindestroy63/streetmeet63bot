from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from config import Settings
from database import Database
from keyboards.admin_menu import ADMIN_STATS_BUTTON, ADMIN_USERS_BUTTON
from services.stats_service import get_full_stats, get_users_overview
from utils.permissions import can_use_admin_messages
from utils.texts import BOT_STATS_TEXT, USERS_STATS_TEXT


def get_router(database: Database, settings: Settings) -> Router:
    router = Router(name="admin_stats")

    @router.message(F.text == ADMIN_USERS_BUTTON)
    async def show_users_stats(message: Message) -> None:
        if not can_use_admin_messages(message, settings):
            return
        users = await get_users_overview(database)
        await message.answer(
            USERS_STATS_TEXT.format(
                total=users["total"],
                active=users["active"],
                blocked=users["blocked"],
            )
        )

    @router.message(F.text == ADMIN_STATS_BUTTON)
    async def show_bot_stats(message: Message) -> None:
        if not can_use_admin_messages(message, settings):
            return
        stats = await get_full_stats(database)
        await message.answer(BOT_STATS_TEXT.format(**stats))

    return router
