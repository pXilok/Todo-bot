"""Схемы информации о пользователе."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import BotState


class UserSettingsOut(BaseModel):
    """Настройки пользователя."""

    model_config = ConfigDict(from_attributes=True)

    tz_offset_minutes: int
    reminders_enabled: bool


class UserTaskCounters(BaseModel):
    """Счётчики задач пользователя."""

    total: int
    done: int
    pending: int
    with_reminder: int


class UserOut(BaseModel):
    """Полная карточка пользователя для GET /api/v1/users/{user_id}."""

    id: int
    username: str | None
    first_name: str | None
    chat_id: int
    created_at: datetime
    last_seen_at: datetime
    state: BotState
    settings: UserSettingsOut
    tasks: UserTaskCounters
    messages_total: int