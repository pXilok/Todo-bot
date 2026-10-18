"""Контракт клиент ↔ сервер: нормализованное событие и список действий."""

from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    field_validator,
    model_validator,
)

from app.core.constants import (
    TELEGRAM_BUTTON_TEXT_MAX_LENGTH,
    TELEGRAM_TEXT_MAX_LENGTH,
    ActionType,
    BotState,
    EventType,
    MediaType,
    Platform,
)
from app.schemas.common import validate_callback_data

TelegramText = Annotated[str, Field(min_length=1, max_length=TELEGRAM_TEXT_MAX_LENGTH)]
MAX_INLINE_COLUMNS = 8


class StrictModel(BaseModel):
    """База для входящих схем: лишние поля запрещены."""

    model_config = ConfigDict(extra="forbid")


class UserPayload(StrictModel):
    """Данные отправителя."""

    id: PositiveInt
    username: str | None = Field(default=None, max_length=64)
    first_name: str | None = Field(default=None, max_length=128)


class NormalizedEvent(StrictModel):
    """Событие мессенджера в платформенно-независимом виде."""

    platform: Platform
    update_id: NonNegativeInt
    user: UserPayload
    chat_id: int
    message_id: PositiveInt | None = None
    type: EventType
    text: str | None = Field(default=None, max_length=TELEGRAM_TEXT_MAX_LENGTH)
    callback_data: str | None = None
    timestamp: AwareDatetime

    _check_callback = field_validator("callback_data")(validate_callback_data)

    @model_validator(mode="after")
    def _check_type_consistency(self) -> Self:
        if self.chat_id == 0:
            raise ValueError("chat_id must not be 0")
        if self.type is EventType.CALLBACK and self.callback_data is None:
            raise ValueError("callback event requires callback_data")
        if self.type is EventType.MESSAGE and self.callback_data is not None:
            raise ValueError("message event must not contain callback_data")
        return self


class InlineButton(StrictModel):
    """Inline-кнопка."""

    text: str = Field(min_length=1, max_length=TELEGRAM_BUTTON_TEXT_MAX_LENGTH)
    callback_data: str

    _check_callback = field_validator("callback_data")(validate_callback_data)


class TextAction(BaseModel):
    """Отправить текст. remove_keyboard убирает reply-клавиатуру."""

    type: Literal[ActionType.TEXT] = ActionType.TEXT
    text: TelegramText
    remove_keyboard: bool = False


class ButtonsAction(BaseModel):
    """Отправить текст с inline-кнопками, разложенными по columns в ряд."""

    type: Literal[ActionType.BUTTONS] = ActionType.BUTTONS
    text: TelegramText
    buttons: list[list[InlineButton]] = Field(min_length=1, max_length=100)
    columns: int = Field(default=1, ge=1, le=MAX_INLINE_COLUMNS)


class KeyboardAction(BaseModel):
    """Отправить текст и показать reply-клавиатуру (ряды кнопок)."""

    type: Literal[ActionType.KEYBOARD] = ActionType.KEYBOARD
    text: TelegramText
    keyboard: list[list[str]] = Field(min_length=1)
    resize: bool = True


class MediaAction(BaseModel):
    """Отправить медиа по URL или file_id."""

    type: Literal[ActionType.MEDIA] = ActionType.MEDIA
    media_type: MediaType
    source: str = Field(min_length=1, description="URL или Telegram file_id")
    caption: str | None = Field(default=None, max_length=1024)


class EditAction(BaseModel):
    """Отредактировать сообщение (по умолчанию то, на кнопку которого нажали)."""

    type: Literal[ActionType.EDIT] = ActionType.EDIT
    message_id: PositiveInt | None = None
    text: TelegramText
    buttons: list[list[InlineButton]] | None = Field(default=None, max_length=100)
    columns: int = Field(default=1, ge=1, le=MAX_INLINE_COLUMNS)


class StateAction(BaseModel):
    """Информирует клиента о новом состоянии (для логов/отладки)."""

    type: Literal[ActionType.STATE] = ActionType.STATE
    state: BotState


Action = Annotated[
    TextAction | ButtonsAction | KeyboardAction | MediaAction | EditAction | StateAction,
    Field(discriminator="type"),
]


class EventResponse(BaseModel):
    """Ответ сервера на событие. Пустой actions означает дубликат или отсутствие реакции."""

    actions: list[Action] = Field(default_factory=list)
    state: BotState | None = None
    duplicate: bool = False