from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database
from keyboards.giveaway import build_giveaway_keyboard
from keyboards.subscription import LegacySubscriptionCallback, SubscriptionCallback, build_subscription_keyboard
from keyboards.user_menu import HOW_IT_WORKS_BUTTON, build_user_menu
from services.user_service import notify_about_new_user, register_user, sync_subscription_status


START_TEXT = (
    "<b>STREETMEET63 — предложка 🚗</b>\n\n"
    "Отправь:\n"
    "• фото\n"
    "• подпись\n"
    "• выбери формат публикации\n\n"
    "<i>После проверки пост опубликуют или отклонят</i>"
)

HOW_IT_WORKS_TEXT = (
    "<b>Как это работает 👇</b>\n\n"
    "Ты отправляешь фото,\n"
    "добавляешь подпись,\n"
    "выбираешь формат публикации.\n\n"
    "<i>Дальше пост уходит на модерацию</i>"
)

SUBSCRIPTION_REQUIRED_TEXT = (
    "<b>Доступ к боту только для подписчиков 📢</b>\n\n"
    "Подпишись на канал и нажми <b>«Проверить подписку»</b>"
)

SUBSCRIPTION_NOT_FOUND_TEXT = "Подписка пока не найдена."
GIVEAWAY_START_TEXT = (
    "<b>🎁 Розыгрыш</b>\n\n"
    "Чтобы участвовать:\n"
    "• подпишись на оба канала\n"
    "• нажми кнопку <b>«Участвовать»</b>"
)


router = Router(name="user_start")
_database: Database | None = None
_settings: Settings | None = None


def get_router(database: Database | None = None, settings: Settings | None = None) -> Router:
    global _database, _settings
    if database is not None:
        _database = database
    if settings is not None:
        _settings = settings
    return router


async def _send_start_menu(message: Message, settings: Settings) -> None:
    await message.answer(
        START_TEXT,
        reply_markup=build_user_menu(is_admin=settings.is_admin(message.from_user.id)),
    )


async def _send_giveaway_menu(message: Message, settings: Settings) -> None:
    await message.answer(
        GIVEAWAY_START_TEXT,
        reply_markup=build_giveaway_keyboard(
            channel_1_url=settings.giveaway_channel_1_url,
            channel_2_url=settings.giveaway_channel_2_url,
        ),
    )


async def _send_subscription_gate(message: Message, settings: Settings, error_text: str | None = None) -> None:
    text = error_text or SUBSCRIPTION_REQUIRED_TEXT
    await message.answer(
        text,
        reply_markup=build_subscription_keyboard(settings.channel_url),
    )


def _is_giveaway_deeplink(message: Message) -> bool:
    raw_text = (message.text or "").strip().lower()
    return raw_text.startswith("/start") and "giveaway" in raw_text


@router.message(CommandStart())
async def start_command(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    await state.clear()

    if message.from_user is None:
        return

    if _database is None or _settings is None:
        await message.answer("Произошла ошибка. Попробуйте ещё раз позже.")
        return

    user, is_new = await register_user(
        database=_database,
        settings=_settings,
        telegram_user=message.from_user,
    )

    if is_new:
        await notify_about_new_user(
            bot=bot,
            database=_database,
            settings=_settings,
            user=user,
        )

    subscription = await sync_subscription_status(
        bot=bot,
        database=_database,
        settings=_settings,
        user_id=message.from_user.id,
    )

    if not subscription.can_check:
        await _send_subscription_gate(
            message=message,
            settings=_settings,
            error_text=subscription.error_text,
        )
        return

    if not subscription.is_subscribed:
        await _send_subscription_gate(message=message, settings=_settings)
        return

    if _is_giveaway_deeplink(message):
        await _send_giveaway_menu(message=message, settings=_settings)
        return

    await _send_start_menu(message=message, settings=_settings)


@router.message(StateFilter(None), F.text == HOW_IT_WORKS_BUTTON)
async def how_it_works(
    message: Message,
) -> None:
    await message.answer(HOW_IT_WORKS_TEXT)


@router.callback_query(SubscriptionCallback.filter(F.action == "check_subscription"))
@router.callback_query(LegacySubscriptionCallback.filter(F.action == "check"))
async def check_subscription_callback(
    callback: CallbackQuery,
    bot: Bot,
) -> None:
    if callback.from_user is None:
        await callback.answer("Не удалось проверить подписку.", show_alert=True)
        return

    if _database is None or _settings is None:
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
        return

    subscription = await sync_subscription_status(
        bot=bot,
        database=_database,
        settings=_settings,
        user_id=callback.from_user.id,
    )

    if not subscription.can_check:
        await callback.answer("Не удалось проверить подписку.", show_alert=True)
        if callback.message is not None:
            await callback.message.edit_text(
                subscription.error_text or SUBSCRIPTION_REQUIRED_TEXT,
                reply_markup=build_subscription_keyboard(_settings.channel_url),
            )
        return

    if not subscription.is_subscribed:
        await callback.answer(SUBSCRIPTION_NOT_FOUND_TEXT, show_alert=True)
        return

    await callback.answer("Подписка подтверждена")

    if callback.message is not None:
        await callback.message.answer(
            START_TEXT,
            reply_markup=build_user_menu(is_admin=_settings.is_admin(callback.from_user.id)),
        )
