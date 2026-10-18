"""Зеркало контракта с сервером: событие, действия, элементы outbox.

Схемы терпимы к форме данных: кнопки можно получить рядами или плоским списком,
лишние поля игнорируются, неизвестное действие пропускается с предупреждением.
"""

import logging
from enum import StrEnum
from typing import Any, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    field_validator,
)

logger = logging.getLogger(__name__)
DEFAULT_COLUMNS = 1


class Platform(StrEnum):
    """Платформа-источник события."""

    TELEGRAM = "telegram"


class EventType(StrEnum):
    """Тип события."""

    MESSAGE = "message"
    CALLBACK = "callback"


class AckStatus(StrEnum):
    """Результат доставки из outbox."""

    SENT = "sent"
    FAILED = "failed"


class UserPayload(BaseModel):
    """Отправитель события."""

    id: int
    username: str | None = None
    first_name: str | None = None


class NormalizedEvent(BaseModel):
    """Событие, которое уходит на POST /api/v1/events."""

    platform: Platform = Platform.TELEGRAM
    update_id: int
    user: UserPayload
    chat_id: int
    message_id: int | None = None
    type: EventType
    text: str | None = None
    callback_data: str | None = None
    timestamp: AwareDatetime


class InlineButton(BaseModel):
    """Inline-кнопка."""

    text: str
    callback_data: str


def _as_rows(value: Any, columns: int | None) -> Any:
    """Приводит кнопки к рядам. Плоский список раскладывается по columns."""
    if not isinstance(value, list) or not value:
        return value
    if all(isinstance(item, list) for item in value):
        return value
    size = columns or DEFAULT_COLUMNS
    return [value[index : index + size] for index in range(0, len(value), size)]


class TextAction(BaseModel):
    """Отправить текст."""

    type: Literal["text"]
    text: str
    remove_keyboard: bool = False


class ButtonsAction(BaseModel):
    """Текст с inline-кнопками."""

    type: Literal["buttons"]
    text: str
    columns: int = DEFAULT_COLUMNS
    buttons: list[list[InlineButton]]

    @field_validator("buttons", mode="before")
    @classmethod
    def _rows(cls, value: Any, info: ValidationInfo) -> Any:
        return _as_rows(value, info.data.get("columns"))


class KeyboardAction(BaseModel):
    """Текст с reply-клавиатурой."""

    type: Literal["keyboard", "reply_keyboard"]
    text: str
    keyboard: list[list[str]]
    resize: bool = True


class MediaAction(BaseModel):
    """Фото или документ по URL либо file_id."""

    type: Literal["media"]
    media_type: Literal["photo", "document"]
    source: str
    caption: str | None = None


class EditAction(BaseModel):
    """Редактирование сообщения. buttons может быть null."""

    type: Literal["edit"]
    message_id: int | None = None
    text: str
    columns: int = DEFAULT_COLUMNS
    buttons: list[list[InlineButton]] | None = None

    @field_validator("buttons", mode="before")
    @classmethod
    def _rows(cls, value: Any, info: ValidationInfo) -> Any:
        return _as_rows(value, info.data.get("columns"))


class StateAction(BaseModel):
    """Информационное действие: новое состояние FSM."""

    type: Literal["state"]
    state: str


Action = TextAction | ButtonsAction | KeyboardAction | MediaAction | EditAction | StateAction
_ACTION_ADAPTER: TypeAdapter[Action] = TypeAdapter(Action)


class EventResponse(BaseModel):
    """Ответ сервера на событие."""

    actions: list[Action] = Field(default_factory=list)
    state: str | None = None
    duplicate: bool = False


def parse_event_response(payload: dict[str, Any]) -> EventResponse:
    """Разбирает ответ сервера. Каждое действие проверяется отдельно."""
    actions: list[Action] = []
    for raw in payload.get("actions", []):
        try:
            actions.append(_ACTION_ADAPTER.validate_python(raw))
        except ValidationError:
            logger.warning("Skipping unsupported action: %.200s", raw)
    return EventResponse(
        actions=actions,
        state=payload.get("state"),
        duplicate=bool(payload.get("duplicate", False)),
    )


class OutboxItem(BaseModel):
    """Сообщение из очереди, которое нужно доставить."""

    id: int
    chat_id: int
    kind: str
    text: str


class OutboxClaimResponse(BaseModel):
    """Ответ POST /api/v1/outbox/claim."""

    items: list[OutboxItem] = Field(default_factory=list)


class OutboxAckItem(BaseModel):
    """Результат доставки одного сообщения."""

    id: int
    status: AckStatus
    error: str | None = None