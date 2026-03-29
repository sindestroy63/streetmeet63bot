from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config import Settings
from database import Database
from services.moderation_service import update_signature, update_text
from utils.formatters import normalize_text
from utils.permissions import can_use_admin_messages


class AdminEditingStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_signature = State()


def get_router(database: Database, settings: Settings) -> Router:
    router = Router(name="admin_editing")

    @router.message(
        StateFilter(AdminEditingStates.waiting_for_text, AdminEditingStates.waiting_for_signature),
        Command("cancel"),
    )
    async def cancel_editing(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await _cleanup_prompt(message, state, clear_state=True, delete_input=True)

    @router.message(StateFilter(AdminEditingStates.waiting_for_text), Command("empty"))
    async def clear_text(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await _save_text(message=message, state=state, database=database, settings=settings, text=None)

    @router.message(StateFilter(AdminEditingStates.waiting_for_text), F.text)
    async def save_text(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await _save_text(
            message=message,
            state=state,
            database=database,
            settings=settings,
            text=normalize_text(message.text),
        )

    @router.message(StateFilter(AdminEditingStates.waiting_for_signature), F.text)
    async def save_signature(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return

        data = await state.get_data()
        post_id = data.get("post_id")
        if post_id is None:
            await _cleanup_prompt(message, state, clear_state=True, delete_input=True)
            return

        updated_post = await update_signature(
            database=database,
            bot=message.bot,
            settings=settings,
            post_id=post_id,
            new_signature=normalize_text(message.text),
        )
        await _cleanup_prompt(message, state, clear_state=True, delete_input=True)

        if updated_post is None:
            await message.answer("Заявка уже обработана или недоступна.")

    @router.message(
        StateFilter(AdminEditingStates.waiting_for_text, AdminEditingStates.waiting_for_signature)
    )
    async def wrong_edit_payload(message: Message) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await message.answer("Нужен текст. Используй /cancel для отмены.")

    return router


async def _save_text(
    *,
    message: Message,
    state: FSMContext,
    database: Database,
    settings: Settings,
    text: str | None,
) -> None:
    data = await state.get_data()
    post_id = data.get("post_id")
    if post_id is None:
        await _cleanup_prompt(message, state, clear_state=True, delete_input=True)
        return

    updated_post = await update_text(
        database=database,
        bot=message.bot,
        settings=settings,
        post_id=post_id,
        new_text=text,
    )
    await _cleanup_prompt(message, state, clear_state=True, delete_input=True)

    if updated_post is None:
        await message.answer("Заявка уже обработана или недоступна.")


async def _cleanup_prompt(
    message: Message,
    state: FSMContext,
    *,
    clear_state: bool,
    delete_input: bool,
) -> None:
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")

    if clear_state:
        await state.clear()

    if prompt_message_id:
        with suppress(TelegramBadRequest):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)

    if delete_input:
        with suppress(TelegramBadRequest):
            await message.delete()
