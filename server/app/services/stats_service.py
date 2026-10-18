"""Агрегированная статистика бота."""

from datetime import timedelta
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.constants import OutboxStatus
from app.repositories import (
    MessageRepository,
    OutboxRepository,
    ProcessedEventRepository,
    TaskRepository,
    UserRepository,
)
from app.schemas.stats import StatsOut

ACTIVE_WINDOW: Final = timedelta(hours=24)


class StatsService:
    """Собирает StatsOut из репозиториев (только чтение)."""

    def __init__(self, session: AsyncSession, clock: Clock = utc_now) -> None:
        self._clock = clock
        self._users = UserRepository(session)
        self._tasks = TaskRepository(session)
        self._messages = MessageRepository(session)
        self._events = ProcessedEventRepository(session)
        self._outbox = OutboxRepository(session)

    async def collect(self) -> StatsOut:
        """Посчитать метрики."""
        counters = await self._tasks.counters()
        return StatsOut(
            users_total=await self._users.count(),
            users_active_24h=await self._users.count_active_since(self._clock() - ACTIVE_WINDOW),
            tasks_total=counters.total,
            tasks_done=counters.done,
            tasks_pending=counters.pending,
            reminders_scheduled=counters.with_reminder,
            messages_total=await self._messages.count(),
            events_processed=await self._events.count(),
            outbox_pending=await self._outbox.count_by_status(OutboxStatus.PENDING),
        )