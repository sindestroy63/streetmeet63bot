from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database
from keyboards.admin_menu import (
    ADMIN_BROADCAST_BUTTON,
    ADMIN_CANCEL_BUTTON,
    AdminCallback,
    build_admin_cancel_keyboard,
    build_admin_menu_keyboard,
    build_broadcast_confirm_keyboard,
)
from services.broadcast_service import broadcast_to_users
from states.admin_states import AdminStates
from utils.permissions import can_use_admin_callbacks, can_use_admin_messages
from utils.texts import (
    ADMIN_PANEL_TEXT,
    BROADCAST_INVALID_TEXT,
    BROADCAST_START_TEXT,
    BROADCAST_SUCCESS_TEMPLATE,
    build_broadcast_preview,
)


def get_router(database: Database, settings: Settings) -> Router:
    router = Router(name="admin_broadcast")

    @router.message(F.text == ADMIN_BROADCAST_BUTTON)
    async def start_broadcast(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await state.clear()
        await state.set_state(AdminStates.waiting_for_broadcast_content)
        await message.answer(BROADCAST_START_TEXT, reply_markup=build_admin_cancel_keyboard())

    @router.message(
        StateFilter(AdminStates.waiting_for_broadcast_content),
        F.text == ADMIN_CANCEL_BUTTON,
    )
    async def cancel_broadcast_input(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await state.clear()
        await message.answer(ADMIN_PANEL_TEXT, reply_markup=build_admin_menu_keyboard())

    @router.message(StateFilter(AdminStates.waiting_for_broadcast_content), F.photo)
    async def receive_broadcast_photo(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await state.set_state(AdminStates.waiting_for_broadcast_confirm)
        await state.update_data(
            broadcast_text=message.caption,
            broadcast_photo=message.photo[-1].file_id,
        )
        await message.answer(
            build_broadcast_preview(text=message.caption, has_photo=True),
            reply_markup=build_broadcast_confirm_keyboard(),
        )

    @router.message(StateFilter(AdminStates.waiting_for_broadcast_content), F.text)
    async def receive_broadcast_text(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await state.set_state(AdminStates.waiting_for_broadcast_confirm)
        await state.update_data(broadcast_text=message.text, broadcast_photo=None)
        await message.answer(
            build_broadcast_preview(text=message.text, has_photo=False),
            reply_markup=build_broadcast_confirm_keyboard(),
        )

    @router.message(StateFilter(AdminStates.waiting_for_broadcast_content))
    async def invalid_broadcast_input(message: Message, state: FSMContext) -> None:
        if not can_use_admin_messages(message, settings):
            return
        await message.answer(BROADCAST_INVALID_TEXT, reply_markup=build_admin_cancel_keyboard())

    @router.callback_query(
        StateFilter(AdminStates.waiting_for_broadcast_confirm),
        AdminCallback.filter(),
    )
    async def confirm_broadcast(
        callback: CallbackQuery,
        callback_data: AdminCallback,
        state: FSMContext,
    ) -> None:
        if not can_use_admin_callbacks(callback, settings):
            await callback.answer("Недостаточно прав.", show_alert=True)
            return
        if callback_data.action not in {"broadcast_send", "broadcast_cancel"}:
            await callback.answer()
            return

        if callback_data.action == "broadcast_cancel":
            await state.clear()
            await callback.answer("Рассылка отменена.")
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(ADMIN_PANEL_TEXT, reply_markup=build_admin_menu_keyboard())
            return

        data = await state.get_data()
        result = await broadcast_to_users(
            database=database,
            bot=callback.bot,
            text=data.get("broadcast_text"),
            photo_file_id=data.get("broadcast_photo"),
        )
        await state.clear()
        await callback.answer("Рассылка отправляется.")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            BROADCAST_SUCCESS_TEMPLATE.format(success=result.success, failed=result.failed),
            reply_markup=build_admin_menu_keyboard(),
        )

    return router
