from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers._fsm_busy_guard import answer_busy_scenario, is_admin_top_level_text, is_top_level_command_text
from keyboards.admin_menu import ADMIN_BROADCAST_BUTTON, ADMIN_CANCEL_BUTTON, build_admin_cancel_keyboard, build_admin_menu

router = Router(name="admin_broadcast")

_database = None
_settings = None


class BroadcastStates(StatesGroup):
    waiting_for_content = State()
    waiting_for_confirmation = State()


class BroadcastCallback(CallbackData, prefix="broadcast"):
    action: str


def get_router(database=None, settings=None):
    global _database, _settings
    if database is not None:
        _database = database
    if settings is not None:
        _settings = settings
    return router


def _main_menu(user_id: int):
    return build_admin_menu()


def _is_admin(user_id: int) -> bool:
    return _settings.is_admin(user_id)


def _build_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отправить",
                    callback_data=BroadcastCallback(action="send_confirm").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=BroadcastCallback(action="cancel_flow").pack(),
                )
            ],
        ]
    )


async def _send_main_menu(message: Message, state: FSMContext, text: str) -> None:
    await state.clear()
    await message.answer(text, reply_markup=_main_menu(message.from_user.id))


async def _send_main_menu_from_callback(callback: CallbackQuery, state: FSMContext, text: str) -> None:
    await state.clear()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.message.answer(text, reply_markup=_main_menu(callback.from_user.id))


@router.message(StateFilter(None), Command("broadcast"))
@router.message(StateFilter(None), F.text == ADMIN_BROADCAST_BUTTON)
async def start_broadcast(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(BroadcastStates.waiting_for_content)
    await message.answer(
        "<b>Рассылка</b>\n\nОтправь текст или фото с подписью, которое нужно разослать всем пользователям.",
        reply_markup=build_admin_cancel_keyboard(),
    )


@router.message(BroadcastStates.waiting_for_content, F.text == ADMIN_CANCEL_BUTTON)
@router.message(BroadcastStates.waiting_for_confirmation, F.text == ADMIN_CANCEL_BUTTON)
async def cancel_broadcast_by_button(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await _send_main_menu(message, state, "❌ Рассылка отменена")


@router.message(BroadcastStates.waiting_for_content, F.text.func(is_top_level_command_text))
@router.message(BroadcastStates.waiting_for_confirmation, F.text.func(is_top_level_command_text))
@router.message(BroadcastStates.waiting_for_confirmation, F.text.func(is_admin_top_level_text))
async def block_top_level_navigation_during_broadcast(message: Message) -> None:
    await answer_busy_scenario(message)


@router.message(BroadcastStates.waiting_for_content)
async def collect_broadcast_content(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return

    text = (message.text or message.caption or "").strip()
    photo_file_id = message.photo[-1].file_id if message.photo else None

    if not text and not photo_file_id:
        await message.answer("Отправь текст или фото с подписью.", reply_markup=build_admin_cancel_keyboard())
        return

    await state.update_data(text=text, photo_file_id=photo_file_id)
    await state.set_state(BroadcastStates.waiting_for_confirmation)

    preview_text = "<b>Проверь рассылку:</b>\n\n" + (text if text else "<i>Фото без текста</i>")
    if photo_file_id:
        await message.answer_photo(
            photo=photo_file_id,
            caption=preview_text,
            reply_markup=_build_confirmation_keyboard(),
        )
    else:
        await message.answer(preview_text, reply_markup=_build_confirmation_keyboard())


@router.callback_query(BroadcastCallback.filter(F.action.in_({"cancel", "cancel_flow"})))
async def cancel_broadcast_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await _send_main_menu_from_callback(callback, state, "❌ Рассылка отменена")
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action.in_({"confirm", "send_confirm"})))
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return

    try:
        await callback.answer("Рассылка запущена")
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    text = data.get("text", "")
    photo_file_id = data.get("photo_file_id")

    success_count = 0
    error_count = 0

    for user in await _database.get_all_users():
        try:
            if photo_file_id:
                await callback.bot.send_photo(chat_id=user.telegram_id, photo=photo_file_id, caption=text or None)
            else:
                await callback.bot.send_message(chat_id=user.telegram_id, text=text or " ")
            success_count += 1
        except TelegramForbiddenError:
            error_count += 1
            await _database.mark_user_blocked(user.telegram_id)
        except TelegramBadRequest:
            error_count += 1
        except Exception:
            error_count += 1

    await _send_main_menu_from_callback(
        callback,
        state,
        "<b>✅ Рассылка завершена</b>\n\n"
        f"<b>Успешно:</b> {success_count}\n"
        f"<b>Ошибок:</b> {error_count}",
    )
