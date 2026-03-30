from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database
from keyboards.admin_menu import ADMIN_GIVEAWAY_BUTTON
from keyboards.giveaway import GiveawayAdminCallback, build_giveaway_admin_keyboard
from services.giveaway_service import (
    draw_giveaway_winners,
    get_giveaway_overview,
    notify_admin_about_giveaway_results,
)


router = Router(name="admin_giveaway")
_database: Database | None = None
_settings: Settings | None = None


def get_router(database: Database | None = None, settings: Settings | None = None) -> Router:
    global _database, _settings
    if database is not None:
        _database = database
    if settings is not None:
        _settings = settings
    return router


def _is_admin(message_or_callback) -> bool:
    return bool(
        _settings
        and getattr(message_or_callback, "from_user", None)
        and _settings.is_admin(message_or_callback.from_user.id)
    )


@router.message(Command("giveaway_admin"))
@router.message(F.text == ADMIN_GIVEAWAY_BUTTON)
async def open_giveaway_admin(message: Message) -> None:
    if not _is_admin(message) or _database is None or _settings is None:
        return

    overview = await get_giveaway_overview(_database, _settings)
    stats = overview["stats"]
    text = (
        "<b>🎁 Розыгрыш</b>\n\n"
        f"<b>Дата розыгрыша:</b> {overview['draw_at'].strftime('%d.%m.%Y %H:%M')}\n"
        f"<b>Победителей:</b> {overview['winners_count']}\n"
        f"<b>Участников:</b> {stats['total']}\n"
        f"<b>Победителей выбрано:</b> {stats['winners']}\n"
        f"<b>Статус:</b> {'завершён' if stats['completed'] else 'активен'}"
    )
    await message.answer(text, reply_markup=build_giveaway_admin_keyboard())


@router.callback_query(GiveawayAdminCallback.filter(F.action == "participants"))
async def show_participants(callback: CallbackQuery) -> None:
    if not _is_admin(callback) or _database is None:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    participants = await _database.get_all_giveaway_participants()
    total = len(participants)
    recent = participants[-10:]

    if recent:
        lines = "\n".join(
            f"• @{item.username}" if item.username else f"• {item.first_name or '—'} / ID {item.telegram_id}"
            for item in recent
        )
    else:
        lines = "Пока нет участников"

    await callback.message.answer(
        "<b>📋 Участники</b>\n\n"
        f"<b>Всего:</b> {total}\n\n"
        f"{lines}"
    )
    await callback.answer()


@router.callback_query(GiveawayAdminCallback.filter(F.action == "stats"))
async def show_giveaway_stats(callback: CallbackQuery) -> None:
    if not _is_admin(callback) or _database is None or _settings is None:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    stats = await _database.get_giveaway_stats()
    await callback.message.answer(
        "<b>📊 Статистика розыгрыша</b>\n\n"
        f"<b>Участников:</b> {stats['total']}\n"
        f"<b>Победителей:</b> {stats['winners']}\n"
        f"<b>Статус:</b> {'завершён' if stats['completed'] else 'активен'}\n"
        f"<b>Дата розыгрыша:</b> {_settings.giveaway_draw_at.strftime('%d.%m.%Y %H:%M')}"
    )
    await callback.answer()


@router.callback_query(GiveawayAdminCallback.filter(F.action == "draw"))
async def draw_winners(callback: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(callback) or _database is None or _settings is None:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    if await _database.is_giveaway_draw_completed():
        await callback.answer("Розыгрыш уже проведён", show_alert=True)
        return

    winners = await draw_giveaway_winners(bot, _database, _settings)
    await notify_admin_about_giveaway_results(bot, _settings, winners)
    await callback.answer("Розыгрыш проведён", show_alert=True)
