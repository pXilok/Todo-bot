"""Действия для клиента. Определения живут в events.py, здесь псевдонимы под имена из сервисов."""

from app.schemas.events import (
    Action,
    ButtonsAction,
    EditAction,
    EventResponse,
    InlineButton,
    KeyboardAction,
    MediaAction,
    StateAction,
    TextAction,
)

ReplyKeyboardAction = KeyboardAction
EditMessageAction = EditAction

__all__ = [
    "Action",
    "ButtonsAction",
    "EditAction",
    "EditMessageAction",
    "EventResponse",
    "InlineButton",
    "KeyboardAction",
    "MediaAction",
    "ReplyKeyboardAction",
    "StateAction",
    "TextAction",
]