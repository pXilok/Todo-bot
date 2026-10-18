"""Слой доступа к данным.

Репозитории не делают commit: границами транзакции управляет сервисный слой.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.messages import MessageRepository
from app.repositories.outbox import OutboxRepository
from app.repositories.processed_events import ProcessedEventRepository
from app.repositories.states import UserStateRepository
from app.repositories.tasks import TaskRepository
from app.repositories.user_settings import UserSettingsRepository
from app.repositories.users import UserRepository

__all__ = [
    "MessageRepository",
    "OutboxRepository",
    "ProcessedEventRepository",
    "Repositories",
    "TaskRepository",
    "UserRepository",
    "UserSettingsRepository",
    "UserStateRepository",
]


@dataclass(frozen=True, slots=True)
class Repositories:
    """Набор репозиториев, которые нужны обработчикам FSM, поверх одной сессии."""

    users: UserRepository
    settings: UserSettingsRepository
    states: UserStateRepository
    tasks: TaskRepository
    messages: MessageRepository

    @classmethod
    def from_session(cls, session: AsyncSession) -> "Repositories":
        """Создать все репозитории, разделяющие одну сессию (одну транзакцию)."""
        return cls(
            users=UserRepository(session),
            settings=UserSettingsRepository(session),
            states=UserStateRepository(session),
            tasks=TaskRepository(session),
            messages=MessageRepository(session),
        )