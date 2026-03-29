from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


ADMIN_PANEL_BUTTON = "⚙️ Админка"
ADMIN_BROADCAST_BUTTON = "📢 Рассылка"
ADMIN_USERS_BUTTON = "👥 Пользователи"
ADMIN_STATS_BUTTON = "📊 Статистика"
ADMIN_CLOSE_BUTTON = "❌ Закрыть"
ADMIN_CANCEL_BUTTON = "❌ Отмена"


class AdminCallback(CallbackData, prefix="adm"):
    action: str


def build_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_BROADCAST_BUTTON)],
            [KeyboardButton(text=ADMIN_USERS_BUTTON), KeyboardButton(text=ADMIN_STATS_BUTTON)],
            [KeyboardButton(text=ADMIN_CLOSE_BUTTON)],
        ],
        resize_keyboard=True,
    )


def build_admin_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=ADMIN_CANCEL_BUTTON)]],
        resize_keyboard=True,
        selective=True,
    )


def build_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data=AdminCallback(action="broadcast_send").pack())
    builder.button(text="❌ Отмена", callback_data=AdminCallback(action="broadcast_cancel").pack())
    builder.adjust(1, 1)
    return builder.as_markup()
