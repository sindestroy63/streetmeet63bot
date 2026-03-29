from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from config import Settings
from database import Database
from keyboards.subscription import SubscriptionCallback, build_subscription_keyboard
from keyboards.user_menu import HOW_IT_WORKS_BUTTON, build_user_menu_keyboard
from services.user_service import notify_about_new_user, register_user, sync_subscription_status
from utils.permissions import can_use_admin_messages
from utils.texts import (
    HOW_IT_WORKS_TEXT,
    START_TEXT,
    SUBSCRIPTION_CHECK_ERROR_TEXT,
    SUBSCRIPTION_NOT_FOUND_ALERT,
    SUBSCRIPTION_REQUIRED_TEXT,
    SUBSCRIPTION_SUCCESS_TEXT,
)


def get_router(database: Database, settings: Settings) -> Router:
    router = Router(name="user_start")

    @router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
    async def start_command(message: Message, state: FSMContext) -> None:
        await _clear_state_prompt(message, state)

        if not message.from_user:
            return

        user, is_new = await register_user(
            database=database,
            settings=settings,
            telegram_user=message.from_user,
        )
        if is_new:
            await notify_about_new_user(bot=message.bot, settings=settings, user=user)

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
            START_TEXT,
            reply_markup=build_user_menu_keyboard(is_admin=settings.is_admin(message.from_user.id)),
        )

    @router.message(F.chat.type == ChatType.PRIVATE, F.text == HOW_IT_WORKS_BUTTON)
    async def how_it_works(message: Message, state: FSMContext) -> None:
        await _clear_state_prompt(message, state)

        if not message.from_user:
            return

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
            HOW_IT_WORKS_TEXT,
            reply_markup=build_user_menu_keyboard(is_admin=settings.is_admin(message.from_user.id)),
        )

    @router.callback_query(SubscriptionCallback.filter())
    async def check_subscription(
        callback: CallbackQuery,
        callback_data: SubscriptionCallback,
        state: FSMContext,
    ) -> None:
        if not callback.from_user:
            await callback.answer()
            return
        if callback_data.action != "check":
            await callback.answer()
            return

        subscription = await sync_subscription_status(
            database=database,
            bot=callback.bot,
            settings=settings,
            user_id=callback.from_user.id,
        )
        if not subscription.can_check:
            await callback.answer("Не удалось проверить подписку.", show_alert=True)
            return

        if not subscription.is_subscribed:
            await callback.answer(SUBSCRIPTION_NOT_FOUND_ALERT, show_alert=True)
            return

        await state.clear()
        with suppress(TelegramBadRequest):
            await callback.message.delete()
        await callback.answer("Подписка подтверждена.")
        await callback.message.answer(
            SUBSCRIPTION_SUCCESS_TEXT,
            reply_markup=ReplyKeyboardRemove(),
        )
        await callback.message.answer(
            START_TEXT,
            reply_markup=build_user_menu_keyboard(is_admin=settings.is_admin(callback.from_user.id)),
        )

    @router.message(Command("chat_id"))
    async def chat_id_command(message: Message) -> None:
        if not can_use_admin_messages(message, settings):
            return

        await message.answer(
            f"chat_id: {message.chat.id}\n"
            f"user_id: {message.from_user.id}"
        )

    @router.channel_post(Command("chat_id"))
    async def channel_chat_id(message: Message) -> None:
        await message.answer(f"chat_id: {message.chat.id}")

    return router


async def _clear_state_prompt(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    if prompt_message_id:
        with suppress(TelegramBadRequest):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
    await state.clear()
