"""ORM-модели. Связи между таблицами только через FK: lazy-loading в async не используем."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import (
    TELEGRAM_CALLBACK_DATA_MAX_BYTES,
    BotState,
    MessageDirection,
    OutboxKind,
    OutboxStatus,
    Platform,
)
from app.db.base import Base, BigIntPK, str_enum, utcnow

USER_FK = "users.id"


class User(Base):
    """Пользователь мессенджера. id — это id в Telegram."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    chat_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class UserSettings(Base):
    """Пользовательские настройки (1:1 с users)."""

    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(USER_FK, ondelete="CASCADE"), primary_key=True
    )
    tz_offset_minutes: Mapped[int] = mapped_column(Integer)
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class UserState(Base):
    """Текущее состояние FSM и контекст (например, выбранный task_id)."""

    __tablename__ = "user_states"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(USER_FK, ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[BotState] = mapped_column(str_enum(BotState), default=BotState.MAIN_MENU)
    data: Mapped[dict[str, Any]] = mapped_column(default=dict)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Task(Base):
    """Задача пользователя с опциональным напоминанием."""

    __tablename__ = "tasks"
    __table_args__ = (Index("ix_tasks_due_reminders", "remind_at", "reminded_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(USER_FK, ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(1000))
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    remind_at: Mapped[datetime | None] = mapped_column()
    reminded_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    done_at: Mapped[datetime | None] = mapped_column()


class Message(Base):
    """История входящих и исходящих сообщений."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(USER_FK, ondelete="CASCADE"), index=True
    )
    direction: Mapped[MessageDirection] = mapped_column(str_enum(MessageDirection))
    text: Mapped[str | None] = mapped_column(Text)
    callback_data: Mapped[str | None] = mapped_column(String(TELEGRAM_CALLBACK_DATA_MAX_BYTES))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class ProcessedEvent(Base):
    """Журнал обработанных update для идемпотентности."""

    __tablename__ = "processed_events"
    __table_args__ = (UniqueConstraint("platform", "update_id"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    platform: Mapped[Platform] = mapped_column(str_enum(Platform))
    update_id: Mapped[int] = mapped_column(BigInteger)
    processed_at: Mapped[datetime] = mapped_column(default=utcnow)


class OutboxMessage(Base):
    """Отложенное исходящее сообщение (напоминание или рассылка)."""

    __tablename__ = "outbox"
    __table_args__ = (Index("ix_outbox_status_created", "status", "created_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey(USER_FK, ondelete="SET NULL")
    )
    task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tasks.id", ondelete="SET NULL")
    )
    kind: Mapped[OutboxKind] = mapped_column(str_enum(OutboxKind))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[OutboxStatus] = mapped_column(
        str_enum(OutboxStatus), default=OutboxStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    claimed_at: Mapped[datetime | None] = mapped_column()
    sent_at: Mapped[datetime | None] = mapped_column()