"""Контекст и результат обработчика, общие хелперы."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from app.core.constants import BotState, EventType
from app.db.models import User, UserSettings
from app.repositories import Repositories
from app.schemas.actions import (
    Action,
    ButtonsAction,
    EditMessageAction,
    InlineButton,
    ReplyKeyboardAction,
    TextAction,
)
from app.schemas.events import NormalizedEvent
from app.services.callbacks import ParsedCallback, parse_callback
from app.services.keyboards import main_menu_keyboard

STATE_DATA_TASK_ID: Final = "task_id"


@dataclass(frozen=True, slots=True)
class HandlerLimits:
    """Ограничения сценария (берутся из Settings)."""

    task_title_max_length: int = 200
    tasks_page_size: int = 20


@dataclass(slots=True)
class HandlerContext:
    """Всё, что нужно обработчику для принятия решения."""

    event: NormalizedEvent
    user: User
    settings: UserSettings
    state: BotState
    state_data: dict[str, Any]
    now: datetime
    repos: Repositories
    limits: HandlerLimits
    callback: ParsedCallback | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.event.type == EventType.CALLBACK and self.event.callback_data:
            self.callback = parse_callback(self.event.callback_data)

    @property
    def text(self) -> str:
        """Текст сообщения без крайних пробелов."""
        return (self.event.text or "").strip()

    @property
    def callback_arg(self) -> int | None:
        """Числовой аргумент callback (обычно id задачи)."""
        return self.callback.arg if self.callback else None

    @property
    def can_edit(self) -> bool:
        """Можно ли отредактировать сообщение с нажатой кнопкой вместо отправки нового."""
        return self.event.type == EventType.CALLBACK and self.event.message_id is not None


@dataclass(slots=True)
class HandlerResult:
    """Действия для клиента и следующее состояние."""

    actions: list[Action]
    state: BotState
    state_data: dict[str, Any] = field(default_factory=dict)


Handler = Callable[[HandlerContext], Awaitable[HandlerResult]]


def stay(ctx: HandlerContext, text: str) -> HandlerResult:
    """Ответить текстом, не меняя состояние и его данные (ошибка ввода)."""
    return HandlerResult(actions=[TextAction(text=text)], state=ctx.state, state_data=ctx.state_data)


def to_main_menu(text: str, *extra: Action) -> HandlerResult:
    """Вернуться в главное меню с восстановлением reply-клавиатуры."""
    return HandlerResult(
        actions=[ReplyKeyboardAction(text=text, keyboard=main_menu_keyboard()), *extra],
        state=BotState.MAIN_MENU,
    )


def show_or_edit(ctx: HandlerContext, text: str, buttons: list[list[InlineButton]]) -> Action:
    """На нажатие кнопки редактировать её сообщение, иначе отправить новое."""
    if ctx.can_edit and ctx.event.message_id is not None:
        return EditMessageAction(message_id=ctx.event.message_id, text=text, buttons=buttons or None)
    if buttons:
        return ButtonsAction(text=text, buttons=buttons)
    return TextAction(text=text)