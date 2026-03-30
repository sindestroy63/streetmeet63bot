from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.moderation_edit import build_moderation_edit_keyboard
from keyboards.moderation_inline import build_edit_cancel_keyboard
from keyboards.moderation_main import ModerationCallback, build_moderation_main_keyboard
from services.moderation_service import publish_post, reject_post
from utils.formatters import format_moderation_card

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


async def _safe_callback_answer(
    callback: CallbackQuery,
    text: str | None = None,
    *,
    show_alert: bool = False,
) -> None:
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest:
        pass


async def _safe_delete_message(bot, chat_id: int | None, message_id: int | None) -> None:
    if not chat_id or not message_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        pass


async def _sync_current_card(callback: CallbackQuery, post_id: int) -> None:
    await _database.set_admin_messages(
        post_id=post_id,
        moderation_chat_id=callback.message.chat.id,
        moderation_message_id=callback.message.message_id,
    )


def _menu_markup(post, menu: str):
    if menu == "edit":
        return build_moderation_edit_keyboard(post)
    return build_moderation_main_keyboard(post)


async def _refresh_card(post_id: int, bot, *, menu: str) -> None:
    post = await _database.get_submission(post_id)
    if not post or not post.moderation_chat_id or not post.moderation_message_id:
        return

    text = format_moderation_card(post, _settings.timezone)
    markup = _menu_markup(post, menu)

    try:
        await bot.edit_message_text(
            chat_id=post.moderation_chat_id,
            message_id=post.moderation_message_id,
            text=text,
            reply_markup=markup,
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error).lower():
            try:
                await bot.edit_message_reply_markup(
                    chat_id=post.moderation_chat_id,
                    message_id=post.moderation_message_id,
                    reply_markup=markup,
                )
            except TelegramBadRequest:
                pass


async def _open_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    post_id: int,
    target_state,
    prompt_text: str,
    field_name: str,
) -> None:
    await _sync_current_card(callback, post_id)
    await state.clear()
    await state.set_state(target_state)
    prompt = await callback.message.answer(
        prompt_text,
        reply_markup=build_edit_cancel_keyboard(post_id, field_name),
    )
    await state.update_data(
        post_id=post_id,
        card_chat_id=callback.message.chat.id,
        card_message_id=callback.message.message_id,
        prompt_chat_id=prompt.chat.id,
        prompt_message_id=prompt.message_id,
    )
    await _safe_callback_answer(callback)


async def _finish_edit(
    message: Message,
    state: FSMContext,
    *,
    post_id: int,
    menu: str = "edit",
) -> None:
    data = await state.get_data()
    await _safe_delete_message(message.bot, data.get("prompt_chat_id"), data.get("prompt_message_id"))
    await _safe_delete_message(message.bot, message.chat.id, message.message_id)
    await state.clear()
    await _refresh_card(post_id, message.bot, menu=menu)


@router.callback_query(ModerationCallback.filter(F.action == "edit_menu"))
async def open_edit_menu(callback: CallbackQuery, callback_data: ModerationCallback) -> None:
    await _sync_current_card(callback, callback_data.post_id)
    await _refresh_card(callback_data.post_id, callback.bot, menu="edit")
    await _safe_callback_answer(callback)


@router.callback_query(ModerationCallback.filter(F.action == "back_main"))
async def back_to_main_menu(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    data = await state.get_data()
    await _safe_delete_message(callback.bot, data.get("prompt_chat_id"), data.get("prompt_message_id"))
    await state.clear()
    await _sync_current_card(callback, callback_data.post_id)
    await _refresh_card(callback_data.post_id, callback.bot, menu="main")
    await _safe_callback_answer(callback)


@router.callback_query(ModerationCallback.filter(F.action == "edit_text"))
async def start_text_edit(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    await _open_prompt(
        callback,
        state,
        post_id=callback_data.post_id,
        target_state=ModerationEditingStates.waiting_for_text,
        prompt_text="Отправьте новый текст поста",
        field_name="text",
    )


@router.callback_query(ModerationCallback.filter(F.action == "edit_signature"))
async def start_signature_edit(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    await _open_prompt(
        callback,
        state,
        post_id=callback_data.post_id,
        target_state=ModerationEditingStates.waiting_for_signature,
        prompt_text="Отправьте новую подпись",
        field_name="signature",
    )


@router.callback_query(ModerationCallback.filter(F.action == "cancel_text"))
@router.callback_query(ModerationCallback.filter(F.action == "cancel_signature"))
async def cancel_edit_prompt(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    data = await state.get_data()
    await _safe_delete_message(callback.bot, data.get("prompt_chat_id"), data.get("prompt_message_id"))
    await state.clear()
    await _sync_current_card(callback, callback_data.post_id)
    await _refresh_card(callback_data.post_id, callback.bot, menu="edit")
    await _safe_callback_answer(callback)


@router.message(ModerationEditingStates.waiting_for_text, F.text)
async def save_edited_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = data["post_id"]
    await _database.update_final_text(post_id=post_id, final_text=message.text.strip())
    await _finish_edit(message, state, post_id=post_id, menu="edit")


@router.message(ModerationEditingStates.waiting_for_signature, F.text)
async def save_edited_signature(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    post_id = data["post_id"]
    signature = message.text.strip()

    await _database.update_signature(post_id=post_id, signature=signature)
    await _database.set_admin_signature(post_id=post_id, is_admin_signature=bool(signature))
    if signature:
        await _database.set_anonymous(post_id=post_id, anonymous=False)

    await _finish_edit(message, state, post_id=post_id, menu="edit")


@router.callback_query(ModerationCallback.filter(F.action == "toggle_anonymous"))
async def toggle_anonymous(callback: CallbackQuery, callback_data: ModerationCallback) -> None:
    await _sync_current_card(callback, callback_data.post_id)
    post = await _database.get_submission(callback_data.post_id)
    if not post:
        await _safe_callback_answer(callback)
        return

    new_value = not bool(post.anonymous)
    await _database.set_anonymous(post_id=post.id, anonymous=new_value)
    await _refresh_card(post.id, callback.bot, menu="edit")
    await _safe_callback_answer(callback, "Анонимность обновлена")


@router.callback_query(ModerationCallback.filter(F.action == "clear_signature"))
async def clear_signature(callback: CallbackQuery, callback_data: ModerationCallback) -> None:
    await _sync_current_card(callback, callback_data.post_id)
    await _database.update_signature(post_id=callback_data.post_id, signature="")
    await _database.set_admin_signature(post_id=callback_data.post_id, is_admin_signature=False)
    await _refresh_card(callback_data.post_id, callback.bot, menu="edit")
    await _safe_callback_answer(callback, "Подпись убрана")


@router.callback_query(ModerationCallback.filter(F.action == "publish"))
async def publish_submission_callback(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    await _safe_callback_answer(callback, "Публикую…")
    await state.clear()
    await _sync_current_card(callback, callback_data.post_id)
    await publish_post(
        bot=callback.bot,
        database=_database,
        settings=_settings,
        post_id=callback_data.post_id,
        moderator_id=callback.from_user.id,
    )


@router.callback_query(ModerationCallback.filter(F.action == "reject"))
async def reject_submission_callback(callback: CallbackQuery, callback_data: ModerationCallback, state: FSMContext) -> None:
    await _safe_callback_answer(callback, "Отклоняю…")
    await state.clear()
    await _sync_current_card(callback, callback_data.post_id)
    await reject_post(
        bot=callback.bot,
        database=_database,
        settings=_settings,
        post_id=callback_data.post_id,
        moderator_id=callback.from_user.id,
    )
