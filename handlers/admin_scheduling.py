from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from handlers._fsm_busy_guard import answer_busy_scenario, is_top_level_command_text
from keyboards.admin_menu import ADMIN_CANCEL_BUTTON, build_admin_cancel_keyboard
from keyboards.moderation_main import LegacyModerationCallback
from keyboards.schedule_inline import LegacyScheduleCallback, ScheduleCallback, build_schedule_keyboard
from keyboards.user_menu import build_user_menu
from services.moderation_service import refresh_moderation_card

router = Router(name="admin_scheduling")
logger = logging.getLogger(__name__)

_database = None
_settings = None


class SchedulingStates(StatesGroup):
    waiting_for_schedule_datetime = State()


SCHEDULE_PRESET_ACTIONS = {
    "set_plus_30m",
    "set_plus_1h",
    "set_today_18",
    "set_today_21",
    "set_tomorrow_12",
    "set_tomorrow_18",
    "plus_30m",
    "plus_1h",
    "today_18",
    "today_21",
    "tomorrow_12",
    "tomorrow_18",
}


def get_router(database=None, settings=None):
    global _database, _settings
    if database is not None:
        _database = database
    if settings is not None:
        _settings = settings
    return router


def _main_menu(user_id: int):
    return build_user_menu(is_admin=_settings.is_admin(user_id))


def _now():
    return datetime.now(_settings.timezone)


def _future_at(hour: int, minute: int, days: int = 0) -> datetime:
    base = _now() + timedelta(days=days)
    target = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if days == 0 and target <= _now():
        target += timedelta(days=1)
    return target


def _preset_datetime(action: str) -> datetime | None:
    current = _now()
    mapping = {
        "set_plus_30m": current + timedelta(minutes=30),
        "set_plus_1h": current + timedelta(hours=1),
        "set_today_18": _future_at(18, 0),
        "set_today_21": _future_at(21, 0),
        "set_tomorrow_12": _future_at(12, 0, days=1),
        "set_tomorrow_18": _future_at(18, 0, days=1),
        "plus_30m": current + timedelta(minutes=30),
        "plus_1h": current + timedelta(hours=1),
        "today_18": _future_at(18, 0),
        "today_21": _future_at(21, 0),
        "tomorrow_12": _future_at(12, 0, days=1),
        "tomorrow_18": _future_at(18, 0, days=1),
    }
    return mapping.get(action)


async def _safe_delete(bot, chat_id: int | None, message_id: int | None) -> None:
    if not chat_id or not message_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass


async def _restore_moderation_card(bot, post_id: int | None) -> None:
    if not post_id:
        return
    post = await _database.get_submission(post_id)
    if post:
        await refresh_moderation_card(bot, _settings, post)


async def _schedule_post(callback: CallbackQuery, post_id: int, scheduled_at: datetime) -> None:
    await _database.schedule_post(
        post_id=post_id,
        scheduled_at=scheduled_at.isoformat(),
        scheduled_by=callback.from_user.id,
    )
    post = await _database.get_submission(post_id)
    if post:
        await refresh_moderation_card(callback.bot, _settings, post)


@router.callback_query(ScheduleCallback.filter(F.action == "open_menu"))
@router.callback_query(LegacyModerationCallback.filter(F.action == "schedule"))
async def open_schedule_menu(callback: CallbackQuery, callback_data) -> None:
    if not _settings.is_admin(callback.from_user.id):
        await callback.answer()
        return
    await _database.set_admin_messages(
        post_id=callback_data.post_id,
        moderation_chat_id=callback.message.chat.id,
        moderation_message_id=callback.message.message_id,
    )
    await callback.message.edit_reply_markup(reply_markup=build_schedule_keyboard(callback_data.post_id))
    await callback.answer()


@router.callback_query(ScheduleCallback.filter(F.action == "cancel_flow"))
@router.callback_query(LegacyScheduleCallback.filter(F.action == "cancel"))
async def cancel_schedule(callback: CallbackQuery, callback_data, state: FSMContext) -> None:
    await state.clear()
    await _restore_moderation_card(callback.bot, callback_data.post_id)
    await callback.answer("Планирование отменено")


@router.callback_query(ScheduleCallback.filter(F.action == "open_manual_input"))
@router.callback_query(LegacyScheduleCallback.filter(F.action == "manual"))
async def request_manual_datetime(callback: CallbackQuery, callback_data, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SchedulingStates.waiting_for_schedule_datetime)
    prompt = await callback.message.answer(
        "<b>Введи дату и время публикации</b>\n\n"
        "Формат: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
        "Пример: <code>05.04.2026 18:00</code>",
        reply_markup=build_admin_cancel_keyboard(),
    )
    await state.update_data(
        post_id=callback_data.post_id,
        prompt_chat_id=prompt.chat.id,
        prompt_message_id=prompt.message_id,
    )
    await callback.answer()


@router.callback_query(ScheduleCallback.filter(F.action.in_(SCHEDULE_PRESET_ACTIONS)))
@router.callback_query(LegacyScheduleCallback.filter(F.action.in_(SCHEDULE_PRESET_ACTIONS)))
async def apply_schedule_preset(callback: CallbackQuery, callback_data) -> None:
    try:
        await callback.answer("Планирую…")
    except TelegramBadRequest:
        pass

    scheduled_at = _preset_datetime(callback_data.action)
    if not scheduled_at:
        await callback.answer()
        return

    await _schedule_post(callback, callback_data.post_id, scheduled_at)


@router.callback_query(F.data.startswith("scheduling:"))
async def unknown_schedule_callback(callback: CallbackQuery) -> None:
    logger.warning(
        "Unknown scheduling callback: data=%s user_id=%s",
        callback.data,
        getattr(callback.from_user, "id", None),
    )
    await callback.answer("Действие больше недоступно. Откройте планирование заново.", show_alert=True)


@router.message(SchedulingStates.waiting_for_schedule_datetime, F.text == ADMIN_CANCEL_BUTTON)
async def cancel_schedule_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = data.get("post_id")
    await _safe_delete(message.bot, data.get("prompt_chat_id"), data.get("prompt_message_id"))
    await _safe_delete(message.bot, message.chat.id, message.message_id)
    await state.clear()
    await _restore_moderation_card(message.bot, post_id)
    await message.answer("❌ Планирование отменено")


@router.message(SchedulingStates.waiting_for_schedule_datetime, F.text.func(is_top_level_command_text))
async def block_top_level_commands_during_manual_scheduling(message: Message) -> None:
    await answer_busy_scenario(message)


@router.message(SchedulingStates.waiting_for_schedule_datetime)
async def save_manual_datetime(message: Message, state: FSMContext) -> None:
    try:
        scheduled_at = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M").replace(tzinfo=_settings.timezone)
    except (TypeError, ValueError):
        await message.answer(
            "<b>Неверный формат даты</b>\n\nИспользуй формат <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>.",
            reply_markup=build_admin_cancel_keyboard(),
        )
        return

    if scheduled_at <= _now():
        await message.answer(
            "<b>Дата уже прошла</b>\n\nВведи время в будущем.",
            reply_markup=build_admin_cancel_keyboard(),
        )
        return

    data = await state.get_data()
    post_id = data.get("post_id")
    await _safe_delete(message.bot, data.get("prompt_chat_id"), data.get("prompt_message_id"))
    await _safe_delete(message.bot, message.chat.id, message.message_id)
    await _database.schedule_post(
        post_id=post_id,
        scheduled_at=scheduled_at.isoformat(),
        scheduled_by=message.from_user.id,
    )

    await state.clear()
    await _restore_moderation_card(message.bot, post_id)
    await message.answer(
        "<b>✅ Публикация запланирована</b>\n\n"
        f"<b>Дата:</b> {scheduled_at.strftime('%d.%m.%Y %H:%M')}",
    )
