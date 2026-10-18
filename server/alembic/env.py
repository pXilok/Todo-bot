"""Окружение Alembic: async-движок, URL из Settings, автогенерация по Base.metadata."""

import asyncio
from logging.config import fileConfig
from pathlib import Path
from typing import Any

from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy import pool
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import load_settings
from app.db import models  # noqa: F401  (регистрирует таблицы в metadata)
from app.db.base import Base, UTCDateTime

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def get_database_url() -> str:
    """URL из alembic.ini / -x, а если его нет, из Settings (DATABASE_URL)."""
    return config.get_main_option("sqlalchemy.url") or load_settings().database_url


def ensure_sqlite_directory(url: str) -> None:
    """Создаёт каталог под файл SQLite: миграции стартуют раньше приложения."""
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, "", ":memory:"):
        Path(str(parsed.database)).parent.mkdir(parents=True, exist_ok=True)


def render_item(type_: str, obj: Any, autogen_context: AutogenContext) -> str | bool:
    """Рендерит UTCDateTime как обычный DateTime, чтобы миграции не импортировали app."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    """Генерирует SQL без подключения к БД (alembic upgrade head --sql)."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=url.startswith("sqlite"),
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Применяет миграции на готовом синхронном соединении."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Открывает async-соединение и прогоняет миграции через run_sync."""
    url = get_database_url()
    ensure_sqlite_directory(url)
    engine = create_async_engine(url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """Точка входа онлайн-режима."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()