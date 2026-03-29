from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import SuggestedPost
from keyboards.schedule_inline import ScheduleCallback
from utils.formatters import build_signature_variants


class ModerationCallback(CallbackData, prefix="mod"):
    action: str
    post_id: int


def build_moderation_keyboard(post: SuggestedPost) -> InlineKeyboardMarkup | None:
    if post.status not in {"pending", "scheduled"}:
        return None

    variants = build_signature_variants(post)
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать", callback_data=ModerationCallback(action="publish", post_id=post.id).pack())
    builder.button(text="⏰ Запланировать", callback_data=ScheduleCallback(action="open", post_id=post.id).pack())
    builder.button(text="❌ Отклонить", callback_data=ModerationCallback(action="reject", post_id=post.id).pack())
    builder.button(text="✏️ Текст", callback_data=ModerationCallback(action="edit_text", post_id=post.id).pack())
    builder.button(text="🏷 Подпись", callback_data=ModerationCallback(action="edit_signature", post_id=post.id).pack())
    builder.button(text="👁 Превью", callback_data=ModerationCallback(action="preview", post_id=post.id).pack())
    builder.button(text="🙈 Анонимно", callback_data=ModerationCallback(action="toggle_anonymous", post_id=post.id).pack())
    builder.button(text="♻️ Сбросить", callback_data=ModerationCallback(action="reset", post_id=post.id).pack())
    builder.button(text="🚫 Снять с плана", callback_data=ScheduleCallback(action="remove", post_id=post.id).pack())
    builder.button(text=variants["user_button"], callback_data=ModerationCallback(action="sign_user", post_id=post.id).pack())
    builder.button(text=variants["from_user_button"], callback_data=ModerationCallback(action="sign_from", post_id=post.id).pack())
    builder.button(text="ID автора", callback_data=ModerationCallback(action="sign_id", post_id=post.id).pack())
    builder.button(text="🗑 Убрать подпись", callback_data=ModerationCallback(action="clear_signature", post_id=post.id).pack())
    builder.adjust(3, 3, 3, 3, 1)
    return builder.as_markup()


def build_edit_cancel_keyboard(post_id: int, field_name: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Отмена",
        callback_data=ModerationCallback(action=f"cancel_{field_name}", post_id=post_id).pack(),
    )
    return builder.as_markup()
