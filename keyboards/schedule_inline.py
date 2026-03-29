from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class ScheduleCallback(CallbackData, prefix="sch"):
    action: str
    post_id: int


def build_schedule_menu_keyboard(post_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="+30 мин", callback_data=ScheduleCallback(action="plus_30", post_id=post_id).pack())
    builder.button(text="+1 час", callback_data=ScheduleCallback(action="plus_60", post_id=post_id).pack())
    builder.button(text="Сегодня 18:00", callback_data=ScheduleCallback(action="today_18", post_id=post_id).pack())
    builder.button(text="Сегодня 21:00", callback_data=ScheduleCallback(action="today_21", post_id=post_id).pack())
    builder.button(text="Завтра 12:00", callback_data=ScheduleCallback(action="tomorrow_12", post_id=post_id).pack())
    builder.button(text="Завтра 18:00", callback_data=ScheduleCallback(action="tomorrow_18", post_id=post_id).pack())
    builder.button(text="📝 Ввести вручную", callback_data=ScheduleCallback(action="manual", post_id=post_id).pack())
    builder.button(text="❌ Отмена", callback_data=ScheduleCallback(action="cancel", post_id=post_id).pack())
    builder.adjust(2, 2, 2, 2)
    return builder.as_markup()
