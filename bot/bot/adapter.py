"""Адаптер между Telegram и сервером.

Telegram-обновление превращается в NormalizedEvent. Действия из ответа сервера
выполняются через Bot API. Бизнес-логики здесь нет.
"""

import logging
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as TelegramUser

from bot.api_client import ApiClient, ServerRejectedError, ServerUnavailableError
from bot.keyboards import build_inline_keyboard, build_reply_keyboard, remove_reply_keyboard
from bot.schemas import (
    Action,
    ButtonsAction,
    EditAction,
    EventType,
    KeyboardAction,
    MediaAction,
    NormalizedEvent,
    StateAction,
    TextAction,
    UserPayload,
)

logger = logging.getLogger(__name__)

SERVICE_UNAVAILABLE_TEXT = "Сервис временно недоступен. Попробуйте через минуту."
INTERNAL_ERROR_TEXT = "Произошла внутренняя ошибка. Попробуйте ещё раз."
MESSAGE_NOT_MODIFIED = "message is not modified"


def _user_payload(user: TelegramUser) -> UserPayload:
    return UserPayload(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
    )


def message_to_event(update_id: int, message: Message) -> NormalizedEvent | None:
    """Обычное сообщение (текст, команда или медиа) превращает в событие message."""
    if message.from_user is None:
        return None
    return NormalizedEvent(
        update_id=update_id,
        user=_user_payload(message.from_user),
        chat_id=message.chat.id,
        message_id=message.message_id,
        type=EventType.MESSAGE,
        text=message.text,
        timestamp=datetime.now(UTC),
    )


def callback_to_event(update_id: int, callback: CallbackQuery) -> NormalizedEvent | None:
    """Нажатие inline-кнопки превращает в событие callback."""
    if callback.data is None:
        return None
    source = callback.message
    return NormalizedEvent(
        update_id=update_id,
        user=_user_payload(callback.from_user),
        chat_id=source.chat.id if source is not None else callback.from_user.id,
        message_id=source.message_id if source is not None else None,
        type=EventType.CALLBACK,
        callback_data=callback.data,
        timestamp=datetime.now(UTC),
    )


async def answer_callback(callback: CallbackQuery) -> None:
    """Убирает индикатор загрузки на кнопке. Ошибка здесь не критична."""
    try:
        await callback.answer()
    except TelegramAPIError as exc:
        logger.debug("answer_callback failed: %s", exc)


async def process_event(bot: Bot, api: ApiClient, event: NormalizedEvent) -> None:
    """Отправляет событие на сервер и выполняет полученные действия."""
    try:
        response = await api.send_event(event)
    except ServerUnavailableError as exc:
        logger.error("Server unavailable: %s", exc)
        await _send_plain(bot, event.chat_id, SERVICE_UNAVAILABLE_TEXT)
        return
    except ServerRejectedError as exc:
        logger.error("Server rejected event: %s", exc)
        await _send_plain(bot, event.chat_id, INTERNAL_ERROR_TEXT)
        return

    if response.duplicate:
        logger.info("Duplicate update skipped: update_id=%s", event.update_id)
        return

    for action in response.actions:
        await execute_action(bot, event, action)


async def execute_action(bot: Bot, event: NormalizedEvent, action: Action) -> None:
    """Выполняет одно действие. Ошибка Telegram в нём не отменяет остальные."""
    try:
        match action:
            case TextAction():
                markup = remove_reply_keyboard() if action.remove_keyboard else None
                await bot.send_message(event.chat_id, action.text, reply_markup=markup)
            case ButtonsAction():
                await bot.send_message(
                    event.chat_id,
                    action.text,
                    reply_markup=build_inline_keyboard(action.buttons),
                )
            case KeyboardAction():
                await bot.send_message(
                    event.chat_id,
                    action.text,
                    reply_markup=build_reply_keyboard(action.keyboard, resize=action.resize),
                )
            case MediaAction():
                await _send_media(bot, event.chat_id, action)
            case EditAction():
                await _apply_edit(bot, event, action)
            case StateAction():
                logger.info("FSM state: %s (chat_id=%s)", action.state, event.chat_id)
    except TelegramAPIError as exc:
        logger.error("Telegram API error on %s: %s", type(action).__name__, exc)


async def _send_plain(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except TelegramAPIError as exc:
        logger.error("Failed to send plain text to chat_id=%s: %s", chat_id, exc)


async def _send_media(bot: Bot, chat_id: int, action: MediaAction) -> None:
    if action.media_type == "photo":
        await bot.send_photo(chat_id, photo=action.source, caption=action.caption)
    else:
        await bot.send_document(chat_id, document=action.source, caption=action.caption)


async def _apply_edit(bot: Bot, event: NormalizedEvent, action: EditAction) -> None:
    markup = build_inline_keyboard(action.buttons)
    if action.message_id is None:
        await bot.send_message(event.chat_id, action.text, reply_markup=markup)
        return
    try:
        await bot.edit_message_text(
            text=action.text,
            chat_id=event.chat_id,
            message_id=action.message_id,
            reply_markup=markup,
        )
    except TelegramBadRequest as exc:
        if MESSAGE_NOT_MODIFIED in str(exc):
            return
        raise