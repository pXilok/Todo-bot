"""Схема общей статистики."""

from pydantic import BaseModel


class StatsOut(BaseModel):
    """Агрегированные метрики бота."""

    users_total: int
    users_active_24h: int
    tasks_total: int
    tasks_done: int
    tasks_pending: int
    reminders_scheduled: int
    messages_total: int
    events_processed: int
    outbox_pending: int