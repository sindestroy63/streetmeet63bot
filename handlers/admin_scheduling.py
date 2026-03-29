from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database
from keyboards.admin_menu import ADMIN_CANCEL_BUTTON, build_admin_cancel_keyboard
from keyboards.schedule_inline import ScheduleCallback, build_schedule_menu_keyboard
from services.moderation_service import refresh_moderation_card
from states.admin_states import AdminStates
from utils.datetime_utils import format_datetime_display, is_future_datetime, parse_manual_datetime, quick_schedule_datetime
from utils.permissions import can_use_admin_callbacks, can_use_admin_messages
from utils.texts import (
    SCHEDULE_CANCELLED_TEXT,
    SCHEDULE_INVALID_FORMAT_TEXT,
    SCHEDULE_MANUAL_TEXT,
    SCHEDULE_MENU_TEXT,
    SCHEDULE_NOT_FOUND_TEXT,
    SCHEDULE_PAST_DATE_TEXT,
    build_schedule_success_text,
)


def get_router(database: Database, settings: Settings) -> Router:
    router = Router(name="admin_scheduling")

    @router.callback_query(ScheduleCallback.filter())
    async def handle_schedule_callback(
        callback: CallbackQuery,
        callback_data: ScheduleCallback,
        state: FSMContext,
    ) -> None:
        if not can_use_admin_callbacks(callback, settings):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return

        post = await database.get_post(callback_data.post_id)
        if post is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        action = callback_data.action

        if action == "open":
            if post.status not in {"pending", "scheduled"}:
                await callback.answer("Заявка уже обработана.", show_alert=True)
                return
            await callback.message.answer(
                SCHEDULE_MENU_TEXT,
                reply_markup=build_schedule_menu_keyboard(post.id),
                reply_to_message_id=post.admin_card_message_id,
            )
            await callback.answer()
            return

        if action == "remove":
            if post.status != "scheduled":
                await callback.answer(SCHEDULE_NOT_FOUND_TEXT, show_alert=True)
                return
            changed = await database.unschedule_post(post.id)
            if not changed:
                await callback.answer(SCHEDULE_NOT_FOUND_TEXT, show_alert=True)
                return
            updated_post = await database.get_post(post.id)
            if updated_post:
                await refresh_moderation_card(callback.bot, settings, updated_post)
            await callback.answer("✅ Планирование отменено")
            return

        if action == "cancel":
            await callback.answer("Отменено.")
            with suppress(TelegramBadRequest):
                await callback.message.delete()
            return

        if action == "manual":
            await _clear_existing_prompt(callback.bot, callback.message.chat.id, state)
            await state.clear()
            await state.set_state(AdminStates.waiting_for_schedule_datetime)
            prompt_message = await callback.message.answer(
                SCHEDULE_MANUAL_TEXT,
                reply_markup=build_admin_cancel_keyboard(),
            )
            await state.update_data(post_id=post.id, prompt_message_id=prompt_message.message_id)
            with suppress(TelegramBadRequest):
                await callback.message.delete()
            await callback.answer("Жду дату и время.")
            return

        if action not in {"plus_30", "plus_60", "today_18", "today_21", "tomorrow_12", "tomorrow_18"}:
            await callback.answer()
            return

        if post.status not in {"pending", "scheduled"}:
            await callback.answer("Заявка уже обработана.", show_alert=True)
            return

        scheduled_dt = quick_schedule_datetime(action, settings.timezone)
        changed = await database.schedule_post(post.id, scheduled_dt.isoformat(), callback.from_user.id)
        if not changed:
            await callback.answer("Не удалось запланировать публикацию.", show_alert=True)
            return

        updated_post = await database.get_post(post.id)
        if updated_post:
            await refresh_moderation_card(callback.bot, settings, updated_post)
        with suppress(TelegramBadRequest):
            await callback.message.delete()
        await callback.answer("✅ Запланировано")
        return

    @router.message(StateFilter(AdminStates.waiting_for_schedule_datetime), F.text == ADMIN_CANCEL_BUTTON)
    async def cancel_schedule_input(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await _clear_existing_prompt(message.bot, message.chat.id, state)
        with suppress(TelegramBadRequest):
            await message.delete()
        await state.clear()
        await message.answer(SCHEDULE_CANCELLED_TEXT)

    @router.message(StateFilter(AdminStates.waiting_for_schedule_datetime), F.text)
    async def handle_manual_schedule_datetime(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return

        data = await state.get_data()
        post_id = data.get("post_id")
        if post_id is None:
            await _clear_existing_prompt(message.bot, message.chat.id, state)
            await state.clear()
            return

        post = await database.get_post(post_id)
        if post is None or post.status not in {"pending", "scheduled"}:
            await _clear_existing_prompt(message.bot, message.chat.id, state)
            await state.clear()
            await message.answer("Заявка уже обработана.")
            return

        try:
            scheduled_dt = parse_manual_datetime(message.text, settings.timezone)
        except ValueError:
            await message.answer(SCHEDULE_INVALID_FORMAT_TEXT, reply_markup=build_admin_cancel_keyboard())
            return

        if not is_future_datetime(scheduled_dt, settings.timezone):
            await message.answer(SCHEDULE_PAST_DATE_TEXT, reply_markup=build_admin_cancel_keyboard())
            return

        changed = await database.schedule_post(post.id, scheduled_dt.isoformat(), message.from_user.id)
        await _clear_existing_prompt(message.bot, message.chat.id, state)
        with suppress(TelegramBadRequest):
            await message.delete()
        await state.clear()

        if not changed:
            await message.answer("Не удалось запланировать публикацию.")
            return

        updated_post = await database.get_post(post.id)
        if updated_post:
            await refresh_moderation_card(message.bot, settings, updated_post)
        await message.answer(build_schedule_success_text(format_datetime_display(scheduled_dt.isoformat(), settings.timezone)))

    return router


async def _clear_existing_prompt(bot, chat_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    if prompt_message_id:
        with suppress(TelegramBadRequest):
            await bot.delete_message(chat_id=chat_id, message_id=prompt_message_id)
    await state.update_data(prompt_message_id=None)
