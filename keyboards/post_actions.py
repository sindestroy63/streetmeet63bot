from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


SUGGEST_POST_URL = "http://t.me/streetmeet63bot"
CHAT_URL = "https://t.me/streetmeet63chat"
GIVEAWAY_URL = "https://t.me/streetmeet63bot?start=giveaway"


def build_post_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📩 Предложка", url=SUGGEST_POST_URL),
                InlineKeyboardButton(text="💬 Чат", url=CHAT_URL),
            ],
            [
                InlineKeyboardButton(text="🎁 Розыгрыш", url=GIVEAWAY_URL),
            ],
        ]
    )
