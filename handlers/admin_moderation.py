from __future__ import annotations

from contextlib import suppress

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import Settings
from database import Database
from handlers.admin_editing import AdminEditingStates
from keyboards.moderation_inline import ModerationCallback, build_edit_cancel_keyboard
from services.moderation_service import (
    apply_signature_variant,
    clear_signature,
    publish_post,
    refresh_moderation_card,
    reject_post,
    reset_post,
    toggle_anonymous,
)
from services.preview_service import send_preview
from utils.permissions import can_use_admin_callbacks


def get_router(database: Database, settings: Settings) -> Router:
    router = Router(name="admin_moderation")

    @router.callback_query(ModerationCallback.filter())
    async def handle_moderation_action(
        callback: CallbackQuery,
        callback_data: ModerationCallback,
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

        if action in {"cancel_text", "cancel_signature"}:
            await _cancel_edit_prompt(callback, state)
            await callback.answer("Отменено.")
            return

        if post.status not in {"pending", "scheduled"}:
            await refresh_moderation_card(callback.bot, settings, post)
            await callback.answer("Заявка уже обработана.", show_alert=True)
            return

        if action == "publish":
            ok, result_text = await publish_post(
                database=database,
                bot=callback.bot,
                settings=settings,
                post=post,
                moderator_id=callback.from_user.id,
            )
            await callback.answer(result_text, show_alert=not ok)
            return

        if action == "reject":
            ok, result_text = await reject_post(
                database=database,
                bot=callback.bot,
                settings=settings,
                post=post,
                moderator_id=callback.from_user.id,
            )
            await callback.answer(result_text, show_alert=not ok)
            return

        if action == "preview":
            try:
                await send_preview(
                    bot=callback.bot,
                    chat_id=settings.admin_chat_id,
                    post=post,
                    reply_to_message_id=post.admin_card_message_id,
                )
            except ValueError:
                await callback.answer("Нечего показывать в превью.", show_alert=True)
                return
            await callback.answer("Превью отправлено.")
            return

        if action == "toggle_anonymous":
            updated_post = await toggle_anonymous(
                database=database,
                bot=callback.bot,
                settings=settings,
                post=post,
            )
            if updated_post is None:
                await callback.answer("Не удалось обновить заявку.", show_alert=True)
                return
            await callback.answer("Режим анонимности переключён.")
            return

        if action == "reset":
            updated_post = await reset_post(
                database=database,
                bot=callback.bot,
                settings=settings,
                post=post,
            )
            if updated_post is None:
                await callback.answer("Не удалось сбросить заявку.", show_alert=True)
                return
            await callback.answer("Заявка сброшена.")
            return

        if action == "sign_user":
            await _apply_signature(callback, database, settings, post, "user")
            return

        if action == "sign_from":
            await _apply_signature(callback, database, settings, post, "from_user")
            return

        if action == "sign_id":
            await _apply_signature(callback, database, settings, post, "user_id")
            return

        if action == "clear_signature":
            updated_post = await clear_signature(
                database=database,
                bot=callback.bot,
                settings=settings,
                post=post,
            )
            if updated_post is None:
                await callback.answer("Не удалось убрать подпись.", show_alert=True)
                return
            await callback.answer("Подпись убрана.")
            return

        if action == "edit_text":
            await _start_editing(callback=callback, state=state, post_id=post.id, mode="text")
            return

        if action == "edit_signature":
            await _start_editing(callback=callback, state=state, post_id=post.id, mode="signature")
            return

        await callback.answer()

    return router


async def _apply_signature(callback: CallbackQuery, database: Database, settings: Settings, post, variant_key: str) -> None:
    updated_post = await apply_signature_variant(
        database=database,
        bot=callback.bot,
        settings=settings,
        post=post,
        variant_key=variant_key,
    )
    if updated_post is None:
        await callback.answer("Не удалось обновить подпись.", show_alert=True)
        return
    await callback.answer("Подпись обновлена.")


async def _start_editing(*, callback: CallbackQuery, state: FSMContext, post_id: int, mode: str) -> None:
    previous_data = await state.get_data()
    previous_prompt_id = previous_data.get("prompt_message_id")
    if previous_prompt_id:
        with suppress(TelegramBadRequest):
            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=previous_prompt_id)

    await state.clear()

    if mode == "text":
        await state.set_state(AdminEditingStates.waiting_for_text)
        prompt_text = "Отправь новый текст. Для очистки используй /empty, для отмены — /cancel."
        cancel_keyboard = build_edit_cancel_keyboard(post_id, "text")
        callback_text = "Жду новый текст."
    else:
        await state.set_state(AdminEditingStates.waiting_for_signature)
        prompt_text = "Отправь новую подпись. Для отмены используй /cancel."
        cancel_keyboard = build_edit_cancel_keyboard(post_id, "signature")
        callback_text = "Жду новую подпись."

    prompt_message = await callback.message.answer(prompt_text, reply_markup=cancel_keyboard)
    await state.update_data(post_id=post_id, prompt_message_id=prompt_message.message_id)
    await callback.answer(callback_text)


async def _cancel_edit_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    with suppress(TelegramBadRequest):
        await callback.message.delete()
