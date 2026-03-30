from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.subscription import build_subscription_keyboard
from keyboards.admin_menu import ADMIN_CANCEL_BUTTON, ADMIN_CLOSE_BUTTON
from keyboards.user_flow import (
    CANCEL_BUTTON,
    SKIP_BUTTON,
    UserSubmissionCallback,
    build_caption_step_keyboard,
    build_confirmation_keyboard,
    build_photo_step_keyboard,
    build_publish_mode_keyboard,
)
from keyboards.user_menu import SEND_POST_BUTTON, build_user_menu
from services.submission_service import check_rate_limit, create_submission, deliver_submission_to_admin
from services.user_service import register_user, sync_subscription_status
from states.submission_states import SubmissionStates

router = Router(name="user_submission")

_database = None
_settings = None


PHOTO_STEP_TEXT = "<b>Шаг 1 из 3 — фото</b>\n\nОтправь фото для поста 👇"
CAPTION_STEP_TEXT = "<b>Шаг 2 из 3 — подпись</b>\n\nОтправь подпись к посту или нажми <b>«Пропустить»</b>"
PUBLISH_MODE_TEXT = "<b>Шаг 3 из 3 — формат публикации</b>\n\nВыбери, как опубликовать пост 👇"
SUCCESS_TEXT = "<b>✅ Предложка отправлена</b>\n\n<i>Мы передали её на модерацию</i>"
CANCEL_TEXT = "❌ Отправка отменена"


def get_router(database=None, settings=None):
    global _database, _settings
    if database is not None:
        _database = database
    if settings is not None:
        _settings = settings
    return router


def _main_menu(user_id: int):
    return build_user_menu(is_admin=_settings.is_admin(user_id))


async def _safe_delete(message: Message | None) -> None:
    if not message:
        return
    try:
        await message.delete()
    except TelegramBadRequest:
        return


async def _clear_prompt_messages(
    state: FSMContext,
    incoming_message: Message | None = None,
    *,
    delete_incoming: bool = True,
) -> None:
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    summary_message_id = data.get("summary_message_id")
    chat_id = incoming_message.chat.id if incoming_message else data.get("chat_id")

    if chat_id and prompt_message_id:
        try:
            await (incoming_message.bot if incoming_message else None).delete_message(
                chat_id=chat_id,
                message_id=prompt_message_id,
            )
        except TelegramBadRequest:
            pass
        except AttributeError:
            pass

    if chat_id and summary_message_id:
        try:
            await (incoming_message.bot if incoming_message else None).delete_message(
                chat_id=chat_id,
                message_id=summary_message_id,
            )
        except TelegramBadRequest:
            pass
        except AttributeError:
            pass

    if incoming_message is not None and delete_incoming:
        await _safe_delete(incoming_message)

    await state.update_data(prompt_message_id=None, summary_message_id=None)


async def _send_main_menu(message: Message, state: FSMContext, text: str = CANCEL_TEXT) -> None:
    await _clear_prompt_messages(state, message, delete_incoming=False)
    await state.clear()
    await message.answer(text, reply_markup=_main_menu(message.from_user.id))


async def _send_photo_step(message: Message, state: FSMContext) -> None:
    prompt = await message.answer(PHOTO_STEP_TEXT, reply_markup=build_photo_step_keyboard())
    await state.update_data(chat_id=message.chat.id, prompt_message_id=prompt.message_id, summary_message_id=None)


async def _send_caption_step(message: Message, state: FSMContext) -> None:
    prompt = await message.answer(CAPTION_STEP_TEXT, reply_markup=build_caption_step_keyboard())
    await state.update_data(chat_id=message.chat.id, prompt_message_id=prompt.message_id)


def _build_summary_text(caption: str, publish_as_author: bool) -> str:
    caption_text = html.escape(caption) if caption else "без подписи"
    mode_text = "от автора" if publish_as_author else "анонимно"
    return (
        "<b>Проверь предложку:</b>\n\n"
        "<b>Фото:</b> ✅\n"
        f"<b>Подпись:</b> {caption_text}\n"
        f"<b>Формат:</b> {mode_text}"
    )


async def _show_confirmation(callback: CallbackQuery, state: FSMContext, publish_as_author: bool) -> None:
    data = await state.get_data()
    summary_text = _build_summary_text(data.get("caption", ""), publish_as_author)
    await state.update_data(publish_as_author=publish_as_author)
    try:
        await callback.message.edit_text(summary_text, reply_markup=build_confirmation_keyboard())
    except TelegramBadRequest:
        await callback.message.answer(summary_text, reply_markup=build_confirmation_keyboard())
    await state.update_data(summary_message_id=callback.message.message_id, chat_id=callback.message.chat.id)


@router.message(F.text == SEND_POST_BUTTON)
async def start_submission(message: Message, state: FSMContext) -> None:
    subscription = await sync_subscription_status(
        bot=message.bot,
        database=_database,
        settings=_settings,
        user_id=message.from_user.id,
    )
    if not subscription.is_subscribed:
        await state.clear()
        await message.answer(
            "<b>Доступ к боту только для подписчиков 📢</b>\n\nПодпишись на канал и нажми <b>«Проверить подписку»</b>",
            reply_markup=build_subscription_keyboard(_settings.channel_url),
        )
        return

    allowed, wait_seconds = await check_rate_limit(_database, _settings, message.from_user.id)
    if not allowed:
        minutes = max(1, round(wait_seconds / 60))
        await state.clear()
        await message.answer(
            f"Подожди ещё примерно {minutes} мин. перед новой предложкой.",
            reply_markup=_main_menu(message.from_user.id),
        )
        return

    await state.clear()
    await state.set_state(SubmissionStates.waiting_for_photo)
    await _send_photo_step(message, state)


@router.message(F.text.in_({CANCEL_BUTTON, ADMIN_CANCEL_BUTTON, ADMIN_CLOSE_BUTTON}))
async def cancel_any_flow(message: Message, state: FSMContext) -> None:
    await _send_main_menu(message, state)


@router.message(SubmissionStates.waiting_for_photo, F.photo)
async def save_photo(message: Message, state: FSMContext) -> None:
    await _clear_prompt_messages(state, message)
    await state.update_data(
        photo_file_id=message.photo[-1].file_id,
        caption="",
        publish_as_author=False,
        chat_id=message.chat.id,
    )
    await state.set_state(SubmissionStates.waiting_for_caption)
    await _send_caption_step(message, state)


@router.message(SubmissionStates.waiting_for_photo)
async def invalid_photo(message: Message, state: FSMContext) -> None:
    await _send_photo_step(message, state)


@router.message(SubmissionStates.waiting_for_caption, F.text == SKIP_BUTTON)
async def skip_caption(message: Message, state: FSMContext) -> None:
    await _clear_prompt_messages(state, message)
    await state.update_data(caption="")
    await state.set_state(SubmissionStates.waiting_for_publish_mode)
    summary = await message.answer(PUBLISH_MODE_TEXT, reply_markup=build_publish_mode_keyboard())
    await state.update_data(summary_message_id=summary.message_id, chat_id=message.chat.id)


@router.message(SubmissionStates.waiting_for_caption, F.text)
async def save_caption(message: Message, state: FSMContext) -> None:
    await _clear_prompt_messages(state, message)
    await state.update_data(caption=message.text.strip())
    await state.set_state(SubmissionStates.waiting_for_publish_mode)
    summary = await message.answer(PUBLISH_MODE_TEXT, reply_markup=build_publish_mode_keyboard())
    await state.update_data(summary_message_id=summary.message_id, chat_id=message.chat.id)


@router.message(SubmissionStates.waiting_for_caption)
async def invalid_caption(message: Message, state: FSMContext) -> None:
    await _send_caption_step(message, state)


@router.callback_query(UserSubmissionCallback.filter(F.action == "mode_author"))
async def choose_author_mode(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state != SubmissionStates.waiting_for_publish_mode.state:
        await callback.answer()
        return
    await state.set_state(SubmissionStates.waiting_for_confirmation)
    await _show_confirmation(callback, state, publish_as_author=True)
    await callback.answer()


@router.callback_query(UserSubmissionCallback.filter(F.action == "mode_anonymous"))
async def choose_anonymous_mode(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state != SubmissionStates.waiting_for_publish_mode.state:
        await callback.answer()
        return
    await state.set_state(SubmissionStates.waiting_for_confirmation)
    await _show_confirmation(callback, state, publish_as_author=False)
    await callback.answer()


@router.callback_query(UserSubmissionCallback.filter(F.action == "restart"))
async def restart_submission(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SubmissionStates.waiting_for_photo)
    await callback.message.delete()
    await _send_photo_step(callback.message, state)
    await callback.answer()


@router.callback_query(UserSubmissionCallback.filter(F.action == "cancel"))
async def cancel_submission_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.message.answer(CANCEL_TEXT, reply_markup=_main_menu(callback.from_user.id))
    await callback.answer()


@router.callback_query(UserSubmissionCallback.filter(F.action == "confirm"))
async def confirm_submission(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state() != SubmissionStates.waiting_for_confirmation.state:
        await callback.answer()
        return

    try:
        await callback.answer("Отправляю…")
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    user, _ = await register_user(_database, _settings, callback.from_user)
    text = data.get("caption", "")
    post = await create_submission(
        _database,
        user,
        data["photo_file_id"],
        text,
        bool(data.get("publish_as_author")),
    )
    await deliver_submission_to_admin(callback.bot, _database, _settings, post)

    await state.clear()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await callback.message.answer(SUCCESS_TEXT, reply_markup=_main_menu(callback.from_user.id))


@router.message(SubmissionStates.waiting_for_publish_mode)
@router.message(SubmissionStates.waiting_for_confirmation)
async def wrong_input_during_inline_steps(message: Message) -> None:
    await message.answer("Используй кнопки ниже 👇")
