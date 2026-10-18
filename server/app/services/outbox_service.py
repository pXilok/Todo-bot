"""Outbox: планирование напоминаний и выдача сообщений клиенту."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.constants import OutboxKind
from app.repositories import OutboxRepository, TaskRepository
from app.schemas.outbox import OutboxAckRequest, OutboxItemOut
from app.services import texts

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OutboxConfig:
    """Параметры очереди из Settings."""

    batch_size: int = 50
    claim_timeout: timedelta = timedelta(seconds=60)
    max_attempts: int = 5


class OutboxService:
    """Протокол claim/ack.

    На каждом claim сервер сначала переносит наступившие напоминания в outbox, поэтому
    отдельный планировщик не нужен. Точность напоминаний равна интервалу опроса клиента.
    """

    def __init__(self, session: AsyncSession, config: OutboxConfig, clock: Clock = utc_now) -> None:
        self._session = session
        self._config = config
        self._clock = clock
        self._outbox = OutboxRepository(session)
        self._tasks = TaskRepository(session)

    async def claim(self) -> list[OutboxItemOut]:
        """Запланировать наступившие напоминания и выдать пачку сообщений."""
        now = self._clock()
        try:
            scheduled = await self._schedule_due_reminders(now)
            items = await self._outbox.claim(
                now=now,
                limit=self._config.batch_size,
                stale_before=now - self._config.claim_timeout,
                max_attempts=self._config.max_attempts,
            )
            result = [OutboxItemOut.model_validate(item) for item in items]
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        if scheduled or result:
            logger.info("Outbox claim: reminders_scheduled=%s items=%s", scheduled, len(result))
        return result

    async def ack(self, request: OutboxAckRequest) -> int:
        """Применить результаты доставки. Возвращает число обновлённых записей."""
        now = self._clock()
        updated = 0
        try:
            for item in request.items:
                if await self._outbox.ack(
                    item_id=item.id,
                    status=item.status,
                    error=item.error,
                    now=now,
                    max_attempts=self._config.max_attempts,
                ):
                    updated += 1
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        return updated

    async def _schedule_due_reminders(self, now: datetime) -> int:
        """Перенести наступившие напоминания в outbox.

        Если у пользователя напоминания выключены, задача помечается напомненной
        без отправки, чтобы после включения не пришла пачка старых уведомлений.
        """
        due = await self._tasks.due_reminders(now=now, limit=self._config.batch_size)
        enqueued = 0
        for reminder in due:
            reminder.task.reminded_at = now
            if not reminder.reminders_enabled:
                continue
            await self._outbox.enqueue(
                chat_id=reminder.chat_id,
                kind=OutboxKind.REMINDER,
                text=texts.REMINDER_MESSAGE.format(title=reminder.task.title, task_id=reminder.task.id),
                now=now,
            )
            enqueued += 1
        return enqueued