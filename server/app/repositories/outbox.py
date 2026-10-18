"""Репозиторий очереди исходящих сообщений (outbox)."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AckStatus, OutboxKind, OutboxStatus
from app.db.models import OutboxMessage

ATTEMPTS_EXHAUSTED_ERROR = "attempts exhausted"


class OutboxRepository:
    """Постановка в очередь, выдача клиенту и подтверждение доставки."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, *, chat_id: int, kind: OutboxKind, text: str, now: datetime) -> None:
        """Поставить одно сообщение в очередь."""
        self._session.add(self._build(chat_id=chat_id, kind=kind, text=text, now=now))

    async def enqueue_many(
        self, *, chat_ids: Sequence[int], kind: OutboxKind, text: str, now: datetime
    ) -> int:
        """Поставить одинаковое сообщение для множества чатов."""
        self._session.add_all(
            [self._build(chat_id=chat_id, kind=kind, text=text, now=now) for chat_id in chat_ids]
        )
        await self._session.flush()
        return len(chat_ids)

    async def claim(
        self, *, now: datetime, limit: int, stale_before: datetime, max_attempts: int
    ) -> list[OutboxMessage]:
        """Выдать пачку к доставке: pending и «зависшие» claimed с истёкшим таймаутом."""
        await self._session.execute(
            update(OutboxMessage)
            .where(
                OutboxMessage.status == OutboxStatus.CLAIMED,
                OutboxMessage.claimed_at < stale_before,
                OutboxMessage.attempts >= max_attempts,
            )
            .values(status=OutboxStatus.FAILED, last_error=ATTEMPTS_EXHAUSTED_ERROR)
        )

        stmt = (
            select(OutboxMessage)
            .where(
                OutboxMessage.attempts < max_attempts,
                or_(
                    OutboxMessage.status == OutboxStatus.PENDING,
                    and_(
                        OutboxMessage.status == OutboxStatus.CLAIMED,
                        OutboxMessage.claimed_at < stale_before,
                    ),
                ),
            )
            .order_by(OutboxMessage.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        items = list((await self._session.scalars(stmt)).all())
        for item in items:
            item.status = OutboxStatus.CLAIMED
            item.claimed_at = now
            item.attempts += 1
        await self._session.flush()
        return items

    async def ack(
        self,
        *,
        item_id: int,
        status: AckStatus,
        error: str | None,
        now: datetime,
        max_attempts: int,
    ) -> bool:
        """Применить результат доставки.

        Неуспешная доставка возвращает сообщение в pending, пока попытки не исчерпаны.

        Returns:
            True, если запись найдена в статусе claimed и обновлена.
        """
        item = await self._session.get(OutboxMessage, item_id)
        if item is None or item.status != OutboxStatus.CLAIMED:
            return False

        if status == AckStatus.SENT:
            item.status = OutboxStatus.SENT
            item.sent_at = now
            item.last_error = None
        else:
            item.last_error = error
            item.status = (
                OutboxStatus.FAILED if item.attempts >= max_attempts else OutboxStatus.PENDING
            )
        return True

    async def count_by_status(self, status: OutboxStatus) -> int:
        """Число сообщений в заданном статусе."""
        stmt = select(func.count()).select_from(OutboxMessage).where(OutboxMessage.status == status)
        return int(await self._session.scalar(stmt) or 0)

    @staticmethod
    def _build(*, chat_id: int, kind: OutboxKind, text: str, now: datetime) -> OutboxMessage:
        return OutboxMessage(
            chat_id=chat_id,
            kind=kind,
            text=text,
            status=OutboxStatus.PENDING,
            attempts=0,
            created_at=now,
        )