from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SEND_POST_BUTTON = "📸 Отправить пост"
HOW_IT_WORKS_BUTTON = "ℹ️ Как это работает"
GIVEAWAY_BUTTON = "🎁 Розыгрыш"
ADMIN_PANEL_BUTTON = "⚙️ Админка"


def build_user_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=SEND_POST_BUTTON)],
        [KeyboardButton(text=HOW_IT_WORKS_BUTTON), KeyboardButton(text=GIVEAWAY_BUTTON)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=ADMIN_PANEL_BUTTON)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def build_user_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    return build_user_menu(is_admin=is_admin)
