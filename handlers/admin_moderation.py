from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.moderation_edit import build_moderation_edit_keyboard
from keyboards.moderation_inline import build_edit_cancel_keyboard
from keyboards.moderation_main import ModerationCallback, build_moderation_main_keyboard
from services.moderation_service import (
    clear_signature,
    preview_post,
    publish_post,
    refresh_moderation_card,
    reject_post,
    reset_post,
    toggle_anonymous,
    update_signature,
    update_text,
)

router = Router(name="admin_moderation")

_database = None
_settings = None


class ModerationEditingStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_signature = State()


def get_router(database=None, settings=None):
    global _database, _settings
    if database is not None:
        _database = database
    if settings is not None:
        _settings = settings
    return router


async def _safe_answer(callback: CallbackQuery, text: str | None = None, *, show_alert: bool = False) -> None:
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest:
        pass


async def _safe_delete(bot, chat_id: int | None, message_id: int | None) -> None:
    if not chat_id or not message_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass


async def _remember_card(callback: CallbackQuery, post_id: int) -> None:
    await _database.set_admin_messages(
        post_id=post_id,
        moderation_chat_id=callback.message.chat.id,
        moderation_message_id=callback.message.message_id,
    )


async def _switch_markup(callback: CallbackQuery, post_id: int, *, edit_mode: bool) -> None:
    post = await _database.get_submission(post_id)
    if not post:
        return
    markup = build_moderation_edit_keyboard(post) if edit_mode else build_moderation_main_keyboard(post)
    try:
        await callback.message.edit_reply_markup(reply_markup=markup)
    except TelegramBadRequest:
        await refresh_moderation_card(callback.bot, _settings, post)


async def _open_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    post_id: int,
    target_state,
    field_name: str,
    prompt_text: str,
) -> None:
    await _remember_card(callback, post_id)
    await state.clear()
    await state.set_state(target_state)
    prompt = await callback.message.answer(
        prompt_text,
        reply_markup=build_edit_cancel_keyboard(post_id, field_name),
    )
    await state.update_data(
        post_id=post_id,
        prompt_chat_id=prompt.chat.id,
        prompt_message_id=prompt.message_id,
    )
    await _safe_answer(callback)


async def _finish_prompt(message: Message, state: FSMContext, *, post_id: int) -> None:
    data = await state.get_data()
    await _safe_delete(message.bot, data.get("prompt_chat_id"), data.get("prompt_message_id"))
    await _safe_delete(message.bot, message.chat.id, message.message_id)
    await state.clear()
    post = await _database.get_submission(post_id)
    await refresh_moderation_card(message.bot, _settings, post)
    if post and post.moderation_chat_id and post.moderation_message_id:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=post.moderation_chat_id,
                message_id=post.moderation_message_id,
                reply_markup=build_moderation_edit_keyboard(post),
            )
        except TelegramBadRequest:
            pass


@router.callback_query(ModerationCallback.filter(F.action == "edit_menu"))
async def open_edit_menu(callback: CallbackQuery, callback_data: ModerationCallback) -> None:
    await _remember_card(callback, callback_data.post_id)
    await _switch_markup(callback, callback_data.post_id, edit_mode=True)
    await _safe_answer(callback)


@router.callback_query(ModerationCallback.filter(F.action == "back_main"))
async def back_main(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    data = await state.get_data()
    await _safe_delete(callback.bot, data.get("prompt_chat_id"), data.get("prompt_message_id"))
    await state.clear()
    await _remember_card(callback, callback_data.post_id)
    await _switch_markup(callback, callback_data.post_id, edit_mode=False)
    await _safe_answer(callback)


@router.callback_query(ModerationCallback.filter(F.action == "edit_text"))
async def start_edit_text(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    await _open_prompt(
        callback,
        state,
        post_id=callback_data.post_id,
        target_state=ModerationEditingStates.waiting_for_text,
        field_name="text",
        prompt_text="Отправьте новый текст поста",
    )


@router.callback_query(ModerationCallback.filter(F.action == "edit_signature"))
async def start_edit_signature(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    await _open_prompt(
        callback,
        state,
        post_id=callback_data.post_id,
        target_state=ModerationEditingStates.waiting_for_signature,
        field_name="signature",
        prompt_text="Отправьте новую подпись",
    )


@router.callback_query(ModerationCallback.filter(F.action.in_({"cancel_text", "cancel_signature"})))
async def cancel_prompt(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    data = await state.get_data()
    await _safe_delete(callback.bot, data.get("prompt_chat_id"), data.get("prompt_message_id"))
    await state.clear()
    await _remember_card(callback, callback_data.post_id)
    await _switch_markup(callback, callback_data.post_id, edit_mode=True)
    await _safe_answer(callback)


@router.message(ModerationEditingStates.waiting_for_text, F.text)
async def save_text_prompt(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = data["post_id"]
    await update_text(
        bot=message.bot,
        database=_database,
        settings=_settings,
        post_id=post_id,
        text=message.text.strip(),
    )
    await _finish_prompt(message, state, post_id=post_id)


@router.message(ModerationEditingStates.waiting_for_signature, F.text)
async def save_signature_prompt(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = data["post_id"]
    await update_signature(
        bot=message.bot,
        database=_database,
        settings=_settings,
        post_id=post_id,
        signature=message.text.strip(),
    )
    await _finish_prompt(message, state, post_id=post_id)


@router.callback_query(ModerationCallback.filter(F.action.in_({"toggle_anonymous", "anonymous"})))
async def toggle_anonymous_callback(callback: CallbackQuery, callback_data: ModerationCallback) -> None:
    await _remember_card(callback, callback_data.post_id)
    await toggle_anonymous(
        bot=callback.bot,
        database=_database,
        settings=_settings,
        post_id=callback_data.post_id,
    )
    post = await _database.get_submission(callback_data.post_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=build_moderation_edit_keyboard(post))
    except TelegramBadRequest:
        pass
    await _safe_answer(callback, "Анонимность обновлена")


@router.callback_query(ModerationCallback.filter(F.action.in_({"clear_signature", "remove_signature"})))
async def clear_signature_callback(callback: CallbackQuery, callback_data: ModerationCallback) -> None:
    await _remember_card(callback, callback_data.post_id)
    await clear_signature(
        bot=callback.bot,
        database=_database,
        settings=_settings,
        post_id=callback_data.post_id,
    )
    post = await _database.get_submission(callback_data.post_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=build_moderation_edit_keyboard(post))
    except TelegramBadRequest:
        pass
    await _safe_answer(callback, "Подпись убрана")


@router.callback_query(ModerationCallback.filter(F.action == "reset"))
async def reset_post_callback(callback: CallbackQuery, callback_data: ModerationCallback) -> None:
    await _remember_card(callback, callback_data.post_id)
    await reset_post(
        bot=callback.bot,
        database=_database,
        settings=_settings,
        post_id=callback_data.post_id,
    )
    post = await _database.get_submission(callback_data.post_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=build_moderation_edit_keyboard(post))
    except TelegramBadRequest:
        pass
    await _safe_answer(callback, "Заявка сброшена")


@router.callback_query(ModerationCallback.filter(F.action == "preview"))
async def preview_callback(callback: CallbackQuery, callback_data: ModerationCallback) -> None:
    await _remember_card(callback, callback_data.post_id)
    await preview_post(
        bot=callback.bot,
        database=_database,
        settings=_settings,
        post_id=callback_data.post_id,
    )
    await _safe_answer(callback, "Превью отправлено")


@router.callback_query(ModerationCallback.filter(F.action == "publish"))
async def publish_callback(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    await state.clear()
    await _remember_card(callback, callback_data.post_id)
    await _safe_answer(callback, "Публикую…")
    await publish_post(
        bot=callback.bot,
        database=_database,
        settings=_settings,
        post_id=callback_data.post_id,
        moderator_id=callback.from_user.id,
    )


@router.callback_query(ModerationCallback.filter(F.action == "reject"))
async def reject_callback(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    await state.clear()
    await _remember_card(callback, callback_data.post_id)
    await _safe_answer(callback, "Отклоняю…")
    await reject_post(
        bot=callback.bot,
        database=_database,
        settings=_settings,
        post_id=callback_data.post_id,
        moderator_id=callback.from_user.id,
    )


@router.callback_query(ModerationCallback.filter())
async def moderation_fallback(callback: CallbackQuery) -> None:
    await _safe_answer(callback, "Кнопка устарела или действие больше недоступно")
