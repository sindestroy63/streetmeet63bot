from __future__ import annotations

import logging
from contextlib import suppress

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database
from keyboards.admin_menu import (
    ADMIN_BROADCAST_BUTTON,
    ADMIN_CLOSE_BUTTON,
    ADMIN_PANEL_BUTTON,
    ADMIN_STATS_BUTTON,
    ADMIN_USERS_BUTTON,
)
from keyboards.subscription import build_subscription_keyboard
from keyboards.user_flow import (
    CANCEL_BUTTON,
    SKIP_BUTTON,
    UserFlowCallback,
    build_caption_step_keyboard,
    build_photo_step_keyboard,
    build_publish_mode_keyboard,
    build_summary_keyboard,
)
from keyboards.user_menu import HOW_IT_WORKS_BUTTON, SEND_POST_BUTTON, build_user_menu_keyboard
from services.submission_service import check_rate_limit, create_submission, deliver_submission_to_admin
from services.user_service import sync_subscription_status
from states.submission_states import SubmissionStates
from utils.formatters import build_default_author_signature, normalize_text
from utils.texts import (
    CANCEL_TEXT,
    FLOW_NOT_STARTED_TEXT,
    MODE_CHOOSE_ONLY_TEXT,
    SEND_PHOTO_ONLY_TEXT,
    SEND_POST_TEXT,
    STEP_CAPTION_INVALID_TEXT,
    STEP_CAPTION_TEXT,
    STEP_MODE_TEXT,
    SUBSCRIPTION_CHECK_ERROR_TEXT,
    SUBSCRIPTION_REQUIRED_TEXT,
    SUCCESS_TEXT,
    build_submission_summary,
)


logger = logging.getLogger(__name__)


def get_router(database: Database, settings: Settings) -> Router:
    router = Router(name="user_submission")

    @router.message(
        StateFilter(
            SubmissionStates.waiting_for_photo,
            SubmissionStates.waiting_for_caption,
            SubmissionStates.waiting_for_publish_mode,
        ),
        F.chat.type == ChatType.PRIVATE,
        F.text == SEND_POST_BUTTON,
    )
    async def restart_submission(message: Message, state: FSMContext) -> None:
        await _start_submission_flow(
            message=message,
            state=state,
            database=database,
            settings=settings,
        )

    @router.message(StateFilter(None), F.chat.type == ChatType.PRIVATE, F.text == SEND_POST_BUTTON)
    async def start_submission(message: Message, state: FSMContext) -> None:
        await _start_submission_flow(
            message=message,
            state=state,
            database=database,
            settings=settings,
        )

    @router.message(SubmissionStates.waiting_for_photo, F.chat.type == ChatType.PRIVATE, F.photo)
    async def receive_photo(message: Message, state: FSMContext) -> None:
        await state.update_data(photo_file_id=message.photo[-1].file_id)
        await state.set_state(SubmissionStates.waiting_for_caption)
        await _send_prompt(
            message=message,
            state=state,
            text=STEP_CAPTION_TEXT,
            reply_markup=build_caption_step_keyboard(),
        )

    @router.message(
        SubmissionStates.waiting_for_photo,
        F.chat.type == ChatType.PRIVATE,
        F.text == CANCEL_BUTTON,
    )
    async def cancel_on_photo_step(message: Message, state: FSMContext) -> None:
        await _cancel_flow(message=message, state=state)

    @router.message(SubmissionStates.waiting_for_photo, F.chat.type == ChatType.PRIVATE)
    async def invalid_photo_step_input(message: Message, state: FSMContext) -> None:
        await _send_prompt(
            message=message,
            state=state,
            text=SEND_PHOTO_ONLY_TEXT,
            reply_markup=build_photo_step_keyboard(),
        )

    @router.message(
        SubmissionStates.waiting_for_caption,
        F.chat.type == ChatType.PRIVATE,
        F.text == CANCEL_BUTTON,
    )
    async def cancel_on_caption_step(message: Message, state: FSMContext) -> None:
        await _cancel_flow(message=message, state=state)

    @router.message(
        SubmissionStates.waiting_for_caption,
        F.chat.type == ChatType.PRIVATE,
        F.text == SKIP_BUTTON,
    )
    async def skip_caption(message: Message, state: FSMContext) -> None:
        await state.update_data(caption=None)
        await _send_publish_mode_prompt(message=message, state=state)

    @router.message(SubmissionStates.waiting_for_caption, F.chat.type == ChatType.PRIVATE, F.text)
    async def receive_caption(message: Message, state: FSMContext) -> None:
        await state.update_data(caption=normalize_text(message.text))
        await _send_publish_mode_prompt(message=message, state=state)

    @router.message(SubmissionStates.waiting_for_caption, F.chat.type == ChatType.PRIVATE)
    async def invalid_caption_step_input(message: Message, state: FSMContext) -> None:
        await _send_prompt(
            message=message,
            state=state,
            text=STEP_CAPTION_INVALID_TEXT,
            reply_markup=build_caption_step_keyboard(),
        )

    @router.callback_query(
        StateFilter(SubmissionStates.waiting_for_publish_mode),
        UserFlowCallback.filter(),
    )
    async def handle_publish_mode(
        callback: CallbackQuery,
        callback_data: UserFlowCallback,
        state: FSMContext,
    ) -> None:
        if not callback.from_user:
            await callback.answer()
            return

        data = await state.get_data()
        photo_file_id = data.get("photo_file_id")
        caption = data.get("caption")
        if not photo_file_id:
            await state.clear()
            await callback.answer("Сценарий сброшен. Начни заново.", show_alert=True)
            await _finish_user_flow(callback.message, CANCEL_TEXT, settings, callback.from_user.id)
            return

        if callback_data.action == "cancel":
            await state.clear()
            await _delete_current_callback_message(callback)
            await callback.answer("Отменено.")
            await callback.message.answer(
                CANCEL_TEXT,
                reply_markup=build_user_menu_keyboard(is_admin=settings.is_admin(callback.from_user.id)),
            )
            return

        if callback_data.action == "edit":
            await state.set_state(SubmissionStates.waiting_for_caption)
            await _delete_current_callback_message(callback)
            await callback.answer("Вернулись к подписи.")
            await _send_prompt(
                message=callback.message,
                state=state,
                text=STEP_CAPTION_TEXT,
                reply_markup=build_caption_step_keyboard(),
            )
            return

        if callback_data.action in {"mode_author", "mode_anonymous"}:
            is_anonymous = callback_data.action == "mode_anonymous"
            signature = (
                None
                if is_anonymous
                else build_default_author_signature(
                    user_id=callback.from_user.id,
                    username=callback.from_user.username,
                    first_name=callback.from_user.full_name,
                )
            )
            mode_label = "анонимно" if is_anonymous else "от автора"
            await state.update_data(anonymous=is_anonymous, signature=signature)
            await callback.message.edit_text(
                build_submission_summary(caption=caption, publish_mode_label=mode_label),
                reply_markup=build_summary_keyboard(),
            )
            await state.update_data(prompt_message_id=callback.message.message_id)
            await callback.answer("Проверь предложку.")
            return

        if callback_data.action == "confirm":
            subscription = await sync_subscription_status(
                database=database,
                bot=callback.bot,
                settings=settings,
                user_id=callback.from_user.id,
            )
            if not subscription.can_check:
                await state.clear()
                await _delete_current_callback_message(callback)
                await callback.message.answer(
                    SUBSCRIPTION_CHECK_ERROR_TEXT,
                    reply_markup=build_subscription_keyboard(settings.channel_url),
                )
                await callback.answer("Подписка не подтверждена.", show_alert=True)
                return
            if not subscription.is_subscribed:
                await state.clear()
                await _delete_current_callback_message(callback)
                await callback.message.answer(
                    SUBSCRIPTION_REQUIRED_TEXT,
                    reply_markup=build_subscription_keyboard(settings.channel_url),
                )
                await callback.answer("Нужна подписка на канал.", show_alert=True)
                return

            anonymous = data.get("anonymous")
            signature = data.get("signature")
            if anonymous is None:
                await callback.answer("Сначала выбери формат публикации.", show_alert=True)
                return

            allowed, wait_seconds = await check_rate_limit(
                database=database,
                user_id=callback.from_user.id,
                cooldown_seconds=settings.submission_cooldown_seconds,
            )
            if not allowed:
                wait_minutes = max(1, wait_seconds // 60)
                await callback.answer(
                    f"Подожди ещё примерно {wait_minutes} мин.",
                    show_alert=True,
                )
                return

            try:
                post = await create_submission(
                    database=database,
                    user=callback.from_user,
                    original_text=caption,
                    file_id=photo_file_id,
                    signature=signature,
                    anonymous=anonymous,
                )
                await deliver_submission_to_admin(
                    bot=callback.bot,
                    database=database,
                    settings=settings,
                    post=post,
                )
            except Exception:
                logger.exception("Failed to complete submission flow for user %s", callback.from_user.id)
                await callback.answer("Не удалось отправить предложку.", show_alert=True)
                return

            await state.clear()
            await _delete_current_callback_message(callback)
            await callback.answer("Отправлено.")
            await callback.message.answer(
                SUCCESS_TEXT,
                reply_markup=build_user_menu_keyboard(is_admin=settings.is_admin(callback.from_user.id)),
            )
            return

        await callback.answer()

    @router.message(
        SubmissionStates.waiting_for_publish_mode,
        F.chat.type == ChatType.PRIVATE,
        F.text == CANCEL_BUTTON,
    )
    async def cancel_on_mode_step(message: Message, state: FSMContext) -> None:
        await _cancel_flow(
            message=message,
            state=state,
            is_admin=bool(message.from_user and settings.is_admin(message.from_user.id)),
        )

    @router.message(SubmissionStates.waiting_for_publish_mode, F.chat.type == ChatType.PRIVATE)
    async def invalid_mode_step_input(message: Message) -> None:
        await message.answer(MODE_CHOOSE_ONLY_TEXT)

    @router.message(
        StateFilter(None),
        F.chat.type == ChatType.PRIVATE,
        (F.photo | F.text),
    )
    async def flow_not_started(message: Message) -> None:
        ignored_texts = {
            HOW_IT_WORKS_BUTTON,
            ADMIN_PANEL_BUTTON,
            ADMIN_BROADCAST_BUTTON,
            ADMIN_USERS_BUTTON,
            ADMIN_STATS_BUTTON,
            ADMIN_CLOSE_BUTTON,
        }
        if message.text and (message.text.startswith("/") or message.text in ignored_texts):
            return
        if message.from_user:
            subscription = await sync_subscription_status(
                database=database,
                bot=message.bot,
                settings=settings,
                user_id=message.from_user.id,
            )
            if not subscription.can_check:
                await message.answer(
                    SUBSCRIPTION_CHECK_ERROR_TEXT,
                    reply_markup=build_subscription_keyboard(settings.channel_url),
                )
                return
            if not subscription.is_subscribed:
                await message.answer(
                    SUBSCRIPTION_REQUIRED_TEXT,
                    reply_markup=build_subscription_keyboard(settings.channel_url),
                )
                return
        await message.answer(
            FLOW_NOT_STARTED_TEXT,
            reply_markup=build_user_menu_keyboard(
                is_admin=bool(message.from_user and settings.is_admin(message.from_user.id))
            ),
        )

    return router


async def _send_publish_mode_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(SubmissionStates.waiting_for_publish_mode)
    await _send_prompt(
        message=message,
        state=state,
        text=STEP_MODE_TEXT,
        reply_markup=build_publish_mode_keyboard(),
    )


async def _send_prompt(*, message: Message, state: FSMContext, text: str, reply_markup) -> None:
    await _clear_prompt(message.bot, message.chat.id, state)
    sent_message = await message.answer(text, reply_markup=reply_markup)
    await state.update_data(prompt_message_id=sent_message.message_id)


async def _start_submission_flow(
    *,
    message: Message,
    state: FSMContext,
    database: Database,
    settings: Settings,
) -> None:
    if not message.from_user:
        return

    await _clear_prompt(message.bot, message.chat.id, state)

    subscription = await sync_subscription_status(
        database=database,
        bot=message.bot,
        settings=settings,
        user_id=message.from_user.id,
    )
    if not subscription.can_check:
        await state.clear()
        await message.answer(
            SUBSCRIPTION_CHECK_ERROR_TEXT,
            reply_markup=build_subscription_keyboard(settings.channel_url),
        )
        return
    if not subscription.is_subscribed:
        await state.clear()
        await message.answer(
            SUBSCRIPTION_REQUIRED_TEXT,
            reply_markup=build_subscription_keyboard(settings.channel_url),
        )
        return

    allowed, wait_seconds = await check_rate_limit(
        database=database,
        user_id=message.from_user.id,
        cooldown_seconds=settings.submission_cooldown_seconds,
    )
    if not allowed:
        wait_minutes = max(1, wait_seconds // 60)
        await message.answer(f"Подожди ещё примерно {wait_minutes} мин. перед новой предложкой.")
        return

    await state.clear()
    await state.set_state(SubmissionStates.waiting_for_photo)
    await _send_prompt(
        message=message,
        state=state,
        text=SEND_POST_TEXT,
        reply_markup=build_photo_step_keyboard(),
    )


async def _clear_prompt(bot, chat_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    if not prompt_message_id:
        return
    with suppress(TelegramBadRequest):
        await bot.delete_message(chat_id=chat_id, message_id=prompt_message_id)
    await state.update_data(prompt_message_id=None)


async def _cancel_flow(*, message: Message, state: FSMContext, is_admin: bool = False) -> None:
    await _clear_prompt(message.bot, message.chat.id, state)
    with suppress(TelegramBadRequest):
        await message.delete()
    await state.clear()
    await message.answer(CANCEL_TEXT, reply_markup=build_user_menu_keyboard(is_admin=is_admin))


async def _delete_current_callback_message(callback: CallbackQuery) -> None:
    with suppress(TelegramBadRequest):
        await callback.message.delete()


async def _finish_user_flow(message: Message, text: str, settings: Settings, user_id: int) -> None:
    await message.answer(text, reply_markup=build_user_menu_keyboard(is_admin=settings.is_admin(user_id)))
