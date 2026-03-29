from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SubmissionStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_caption = State()
    waiting_for_publish_mode = State()
