"""Фоновая задача: забирает напоминания и рассылки с сервера и отправляет их."""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.api_client import ApiClient
from bot.schemas import AckStatus, OutboxAckItem, OutboxItem

logger = logging.getLogger(__name__)
MAX_ERROR_LENGTH = 500


async def run_outbox_poller(bot: Bot, api: ApiClient, interval: float) -> None:
    """Бесконечно опрашивает outbox с паузой interval секунд."""
    logger.info("Outbox poller started (interval=%s s)", interval)
    while True:
        try:
            await poll_once(bot, api)
        except Exception:
            logger.exception("Outbox poll failed, will retry")
        await asyncio.sleep(interval)


async def poll_once(bot: Bot, api: ApiClient) -> None:
    """Один цикл: claim, отправка, ack."""
    claimed = await api.claim_outbox()
    if not claimed.items:
        return

    results: list[OutboxAckItem] = []
    for item in claimed.items:
        results.append(await _deliver(bot, item))
    await api.ack_outbox(results)
    logger.info("Outbox delivered: %s item(s)", len(results))


async def _deliver(bot: Bot, item: OutboxItem) -> OutboxAckItem:
    try:
        await bot.send_message(item.chat_id, item.text)
    except TelegramAPIError as exc:
        logger.warning("Delivery failed: outbox_id=%s error=%s", item.id, exc)
        return OutboxAckItem(
            id=item.id,
            status=AckStatus.FAILED,
            error=str(exc)[:MAX_ERROR_LENGTH],
        )
    return OutboxAckItem(id=item.id, status=AckStatus.SENT)