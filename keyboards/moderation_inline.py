from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.moderation_main import ModerationCallback, build_moderation_main_keyboard


def build_moderation_keyboard(post) -> InlineKeyboardMarkup:
    return build_moderation_main_keyboard(post)


def build_edit_cancel_keyboard(post_id: int, field_name: str) -> InlineKeyboardMarkup:
    action = "cancel_text_edit" if field_name == "text" else "cancel_signature_edit"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=ModerationCallback(action=action, post_id=post_id).pack(),
                )
            ]
        ]
    )
