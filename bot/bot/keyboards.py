"""Построители клавиатур aiogram из данных контракта."""

from collections.abc import Sequence

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.schemas import InlineButton


def build_inline_keyboard(
    rows: Sequence[Sequence[InlineButton]] | None,
) -> InlineKeyboardMarkup | None:
    """Строит inline-клавиатуру из рядов кнопок. Пустой вход даёт None."""
    if not rows:
        return None
    keyboard = [
        [
            InlineKeyboardButton(text=button.text, callback_data=button.callback_data)
            for button in row
        ]
        for row in rows
        if row
    ]
    if not keyboard:
        return None
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_reply_keyboard(rows: Sequence[Sequence[str]], *, resize: bool) -> ReplyKeyboardMarkup:
    """Строит reply-клавиатуру из рядов подписей."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=label) for label in row] for row in rows],
        resize_keyboard=resize,
    )


def remove_reply_keyboard() -> ReplyKeyboardRemove:
    """Разметка, которая убирает reply-клавиатуру."""
    return ReplyKeyboardRemove()