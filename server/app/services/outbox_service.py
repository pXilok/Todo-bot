"""Очередь исходящих сообщений: напоминания и выдача клиенту (claim/ack)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import AckStatus, OutboxKind, OutboxStatus
from app.db.models import OutboxMessage, Task, User, UserSettings
from app.schemas.outbox import (
    OutboxAckRequest,
    OutboxAckResponse,
    OutboxClaimResponse,
    OutboxItemOut,
)

REMINDER_TEXT = "⏰ Напоминание: {title} (задача #{task_id})"


class OutboxService:
    """Выдача сообщений клиенту и подтверждение доставки."""

    def __init__(self, session: AsyncSession, *, settings: Settings) -> None:
        self._session = session
        self._batch_size = settings.outbox_batch_size
        self._claim_timeout = timedelta(seconds=settings.outbox_claim_timeout_seconds)
        self._max_attempts = settings.outbox_max_attempts

    async def claim(self) -> OutboxClaimResponse:
        """Создать напоминания по наступившим задачам и отдать пачку сообщений."""
        now = datetime.now(UTC)
        await self._schedule_due_reminders(now)

        stale_before = now - self._claim_timeout
        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.attempts < self._max_attempts)
            .where(
                or_(
                    OutboxMessage.status == OutboxStatus.PENDING,
                    and_(
                        OutboxMessage.status == OutboxStatus.CLAIMED,
                        OutboxMessage.claimed_at < stale_before,
                    ),
                )
            )
            .order_by(OutboxMessage.id)
            .limit(self._batch_size)
        )
        rows = list((await self._session.scalars(stmt)).all())
        for row in rows:
            row.status = OutboxStatus.CLAIMED
            row.claimed_at = now
            row.attempts += 1
        await self._session.commit()

        return OutboxClaimResponse(
            items=[OutboxItemOut.model_validate(row) for row in rows]
        )

    async def ack(self, request: OutboxAckRequest) -> OutboxAckResponse:
        """Записать результаты доставки."""
        now = datetime.now(UTC)
        updated = 0
        for item in request.items:
            row = await self._session.get(OutboxMessage, item.id)
            if row is None or row.status != OutboxStatus.CLAIMED:
                continue
            if item.status == AckStatus.SENT:
                row.status = OutboxStatus.SENT
                row.sent_at = now
                row.last_error = None
            else:
                row.last_error = item.error
                row.status = (
                    OutboxStatus.FAILED
                    if row.attempts >= self._max_attempts
                    else OutboxStatus.PENDING
                )
            updated += 1
        await self._session.commit()
        return OutboxAckResponse(updated=updated)

    async def _schedule_due_reminders(self, now: datetime) -> None:
        """Переносит наступившие напоминания в outbox. Выключенные помечаются без отправки."""
        stmt = (
            select(Task, User.chat_id, UserSettings.reminders_enabled)
            .join(User, User.id == Task.user_id)
            .join(UserSettings, UserSettings.user_id == Task.user_id)
            .where(
                Task.remind_at.is_not(None),
                Task.reminded_at.is_(None),
                Task.is_done.is_(False),
                Task.remind_at <= now,
            )
            .limit(self._batch_size)
        )
        rows = (await self._session.execute(stmt)).all()
        for task, chat_id, reminders_enabled in rows:
            task.reminded_at = now
            if not reminders_enabled:
                continue
            self._session.add(
                OutboxMessage(
                    chat_id=chat_id,
                    user_id=task.user_id,
                    task_id=task.id,
                    kind=OutboxKind.REMINDER,
                    text=REMINDER_TEXT.format(title=task.title, task_id=task.id),
                    status=OutboxStatus.PENDING,
                    attempts=0,
                    created_at=now,
                )
            )
        await self._session.flush()