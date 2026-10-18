"""Декларативная база, общие типы колонок и naming convention для Alembic."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Dialect, Integer, MetaData
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

from app.core.constants import ENUM_COLUMN_LENGTH

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# BIGINT в PostgreSQL, INTEGER в SQLite: только INTEGER PRIMARY KEY автоинкрементится в SQLite.
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


def utcnow() -> datetime:
    """Текущее время в UTC с tzinfo."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """DateTime, гарантирующий хранение и чтение в UTC с tzinfo (в т.ч. на SQLite)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime is not allowed; use timezone-aware UTC values")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def str_enum(enum_cls: type[StrEnum]) -> SAEnum:
    """Enum-колонка как VARCHAR с хранением значений (а не имён) членов."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=ENUM_COLUMN_LENGTH,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        datetime: UTCDateTime(timezone=True),
        dict[str, Any]: JSON(),
    }