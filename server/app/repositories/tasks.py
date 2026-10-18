"""Репозиторий задач."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task, User, UserSettings


@dataclass(frozen=True, slots=True)
class TaskCounters:
    """Агрегаты по задачам."""

    total: int
    done: int
    with_reminder: int

    @property
    def pending(self) -> int:
        """Невыполненные задачи."""
        return self.total - self.done


@dataclass(frozen=True, slots=True)
class DueReminder:
    """Задача, у которой наступило время напоминания."""

    task: Task
    chat_id: int
    reminders_enabled: bool


def _count_if(condition: ColumnElement[bool]) -> ColumnElement[int]:
    """Переносимый аналог COUNT(*) FILTER (WHERE ...) для SQLite и PostgreSQL."""
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


def _reminder_scheduled() -> ColumnElement[bool]:
    """Напоминание назначено, ещё не отправлено, задача не выполнена."""
    return and_(
        Task.remind_at.is_not(None),
        Task.reminded_at.is_(None),
        Task.is_done.is_(False),
    )


class TaskRepository:
    """CRUD задач и выборки для напоминаний."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: int, title: str, now: datetime) -> Task:
        """Создать задачу. flush нужен, чтобы сразу получить id."""
        task = Task(user_id=user_id, title=title, is_done=False, created_at=now)
        self._session.add(task)
        await self._session.flush()
        return task

    async def get_for_user(self, task_id: int, user_id: int) -> Task | None:
        """Задача по id, только если она принадлежит пользователю."""
        stmt = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        return await self._session.scalar(stmt)

    async def list_for_user(self, user_id: int, *, limit: int) -> Sequence[Task]:
        """Сначала активные задачи, внутри групп новые выше."""
        stmt = (
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.is_done.asc(), Task.created_at.desc(), Task.id.desc())
            .limit(limit)
        )
        return (await self._session.scalars(stmt)).all()

    async def mark_done(self, task: Task, *, now: datetime) -> None:
        """Отметить выполнение."""
        task.is_done = True
        task.done_at = now

    async def delete(self, task: Task) -> None:
        """Удалить задачу."""
        await self._session.delete(task)

    async def set_reminder(self, task: Task, remind_at: datetime) -> None:
        """Назначить или перенести напоминание и сбросить признак отправки."""
        task.remind_at = remind_at
        task.reminded_at = None

    async def counters_for_user(self, user_id: int) -> TaskCounters:
        """Счётчики задач одного пользователя."""
        return await self._counters(Task.user_id == user_id)

    async def counters(self) -> TaskCounters:
        """Счётчики по всем задачам."""
        return await self._counters()

    async def due_reminders(self, *, now: datetime, limit: int) -> list[DueReminder]:
        """Задачи, по которым пора напомнить.

        FOR UPDATE SKIP LOCKED на PostgreSQL не даёт двум параллельным claim
        взять одну задачу. SQLite эту конструкцию игнорирует, ему она и не нужна:
        запись там сериализована.
        """
        stmt = (
            select(Task, User.chat_id, UserSettings.reminders_enabled)
            .join(User, User.id == Task.user_id)
            .join(UserSettings, UserSettings.user_id == Task.user_id)
            .where(_reminder_scheduled(), Task.remind_at <= now)
            .order_by(Task.remind_at, Task.id)
            .limit(limit)
            .with_for_update(of=Task, skip_locked=True)
        )
        rows = (await self._session.execute(stmt)).tuples().all()
        return [
            DueReminder(task=task, chat_id=chat_id, reminders_enabled=enabled)
            for task, chat_id, enabled in rows
        ]

    async def _counters(self, *filters: ColumnElement[bool]) -> TaskCounters:
        stmt = select(
            func.count(Task.id),
            _count_if(Task.is_done.is_(True)),
            _count_if(_reminder_scheduled()),
        ).where(*filters)
        total, done, with_reminder = (await self._session.execute(stmt)).one()
        return TaskCounters(total=int(total), done=int(done), with_reminder=int(with_reminder))