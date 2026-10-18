"""Точка входа бота: long polling Telegram и фоновый опрос outbox."""

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.types import CallbackQuery, Message, Update

from bot.adapter import (
    answer_callback,
    callback_to_event,
    message_to_event,
    process_event,
)
from bot.api_client import ApiClient
from bot.config import load_settings
from bot.outbox_poller import run_outbox_poller

logger = logging.getLogger(__name__)
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

router = Router(name="telegram")


@router.message()
async def on_message(
    message: Message,
    event_update: Update,
    bot: Bot,
    api: ApiClient,
) -> None:
    """Любое сообщение пользователя уходит на сервер."""
    event = message_to_event(event_update.update_id, message)
    if event is not None:
        await process_event(bot, api, event)


@router.callback_query()
async def on_callback(
    callback: CallbackQuery,
    event_update: Update,
    bot: Bot,
    api: ApiClient,
) -> None:
    """Нажатие inline-кнопки уходит на сервер."""
    await answer_callback(callback)
    event = callback_to_event(event_update.update_id, callback)
    if event is not None:
        await process_event(bot, api, event)


async def main() -> None:
    """Запускает polling и фоновый опрос outbox."""
    settings = load_settings()
    logging.basicConfig(level=settings.log_level, format=LOG_FORMAT)

    bot = Bot(token=settings.bot_token.get_secret_value())
    api = ApiClient(
        settings.server_url,
        settings.service_token.get_secret_value(),
        timeout=settings.http_timeout_seconds,
        retries=settings.http_retries,
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    poller = asyncio.create_task(
        run_outbox_poller(bot, api, settings.outbox_poll_interval)
    )
    logger.info("Bot started, server=%s", settings.server_url)
    try:
        await dispatcher.start_polling(bot, api=api)
    finally:
        poller.cancel()
        await api.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())