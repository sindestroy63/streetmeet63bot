from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from keyboards.admin_menu import ADMIN_PANEL_BUTTON


SEND_POST_BUTTON = "📸 Отправить пост"
HOW_IT_WORKS_BUTTON = "ℹ️ Как это работает"


def build_user_menu_keyboard(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=SEND_POST_BUTTON)],
        [KeyboardButton(text=HOW_IT_WORKS_BUTTON)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=ADMIN_PANEL_BUTTON)])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
