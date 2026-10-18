"""Схемы админских операций."""

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import TELEGRAM_TEXT_MAX_LENGTH


class BroadcastRequest(BaseModel):
    """Запрос рассылки всем пользователям."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=TELEGRAM_TEXT_MAX_LENGTH)


class BroadcastResponse(BaseModel):
    """Результат постановки рассылки в очередь."""

    queued: int