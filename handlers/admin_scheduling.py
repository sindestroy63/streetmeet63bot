from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.admin_menu import build_admin_cancel_keyboard
from keyboards.moderation_main import ModerationCallback
from keyboards.schedule_inline import ScheduleCallback, build_schedule_keyboard
from keyboards.user_menu import build_user_menu
from services.moderation_service import refresh_moderation_card

router = Router(name="admin_scheduling")

_database = None
_settings = None


class SchedulingStates(StatesGroup):
    waiting_for_schedule_datetime = State()


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
        "plus_30m": current + timedelta(minutes=30),
        "plus_1h": current + timedelta(hours=1),
        "today_18": _future_at(18, 0),
        "today_21": _future_at(21, 0),
        "tomorrow_12": _future_at(12, 0, days=1),
        "tomorrow_18": _future_at(18, 0, days=1),
    }
    return mapping.get(action)


async def _schedule_post(callback: CallbackQuery, post_id: int, scheduled_at: datetime) -> None:
    await _database.schedule_post(
        post_id=post_id,
        scheduled_at=scheduled_at.isoformat(),
        scheduled_by=callback.from_user.id,
    )
    post = await _database.get_submission(post_id)
    if post:
        await refresh_moderation_card(callback.bot, _settings, post)


@router.callback_query(ModerationCallback.filter(F.action == "schedule"))
async def open_schedule_menu(callback: CallbackQuery, callback_data: ModerationCallback) -> None:
    if not _settings.is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.message.edit_reply_markup(reply_markup=build_schedule_keyboard(callback_data.post_id))
    await callback.answer()


@router.callback_query(ScheduleCallback.filter(F.action == "cancel"))
async def cancel_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.message.answer("❌ Планирование отменено", reply_markup=_main_menu(callback.from_user.id))
    await callback.answer()


@router.callback_query(ScheduleCallback.filter(F.action == "manual"))
async def request_manual_datetime(callback: CallbackQuery, callback_data: ScheduleCallback, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SchedulingStates.waiting_for_schedule_datetime)
    await state.update_data(post_id=callback_data.post_id)
    await callback.message.answer(
        "<b>Введи дату и время публикации</b>\n\n"
        "Формат: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
        "Пример: <code>05.04.2026 18:00</code>",
        reply_markup=build_admin_cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(ScheduleCallback.filter())
async def apply_schedule_preset(callback: CallbackQuery, callback_data: ScheduleCallback) -> None:
    if callback_data.action in {"manual", "cancel"}:
        await callback.answer()
        return

    try:
        await callback.answer("Планирую…")
    except TelegramBadRequest:
        pass

    scheduled_at = _preset_datetime(callback_data.action)
    if not scheduled_at:
        await callback.answer()
        return

    await _schedule_post(callback, callback_data.post_id, scheduled_at)


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
    await _database.schedule_post(
        post_id=post_id,
        scheduled_at=scheduled_at.isoformat(),
        scheduled_by=message.from_user.id,
    )
    post = await _database.get_submission(post_id)
    if post:
        await refresh_moderation_card(message.bot, _settings, post)

    await state.clear()
    await message.answer(
        "<b>✅ Публикация запланирована</b>\n\n"
        f"<b>Дата:</b> {scheduled_at.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=_main_menu(message.from_user.id),
    )
