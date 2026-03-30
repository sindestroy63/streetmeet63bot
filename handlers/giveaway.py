from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database
from keyboards.giveaway import GiveawayCallback, build_giveaway_keyboard
from keyboards.user_menu import GIVEAWAY_BUTTON
from services.giveaway_service import check_giveaway_subscriptions, join_giveaway


router = Router(name="giveaway")
_database: Database | None = None
_settings: Settings | None = None


GIVEAWAY_TEXT = (
    "<b>🎁 Розыгрыш</b>\n\n"
    "Чтобы участвовать:\n"
    "• подпишись на оба канала\n"
    "• нажми кнопку <b>«Участвовать»</b>"
)


def get_router(database: Database | None = None, settings: Settings | None = None) -> Router:
    global _database, _settings
    if database is not None:
        _database = database
    if settings is not None:
        _settings = settings
    return router


def _keyboard():
    assert _settings is not None
    return build_giveaway_keyboard(
        channel_1_url=_settings.giveaway_channel_1_url,
        channel_2_url=_settings.giveaway_channel_2_url,
    )


@router.message(Command("giveaway"))
@router.message(F.text == GIVEAWAY_BUTTON)
async def show_giveaway(message: Message) -> None:
    if _settings is None:
        await message.answer("Произошла ошибка. Попробуйте позже.")
        return
    await message.answer(GIVEAWAY_TEXT, reply_markup=_keyboard())


@router.callback_query(GiveawayCallback.filter(F.action == "join"))
async def join_callback(callback: CallbackQuery, bot: Bot) -> None:
    if _database is None or _settings is None or callback.from_user is None:
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
        return

    is_valid, _created = await join_giveaway(
        bot=bot,
        database=_database,
        settings=_settings,
        telegram_user=callback.from_user,
    )

    if not is_valid:
        await callback.answer("❌ Подпишись на оба канала", show_alert=True)
        return

    await callback.answer("✅ Ты участвуешь в розыгрыше", show_alert=True)


@router.callback_query(GiveawayCallback.filter(F.action == "check"))
async def check_callback(callback: CallbackQuery, bot: Bot) -> None:
    if _settings is None or callback.from_user is None:
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
        return

    result = await check_giveaway_subscriptions(
        bot=bot,
        settings=_settings,
        user_id=callback.from_user.id,
    )

    if result.is_valid:
        await callback.answer("✅ Подписки подтверждены", show_alert=True)
    else:
        await callback.answer("❌ Подпишись на оба канала", show_alert=True)
