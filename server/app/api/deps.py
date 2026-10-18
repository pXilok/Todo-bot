"""FastAPI-зависимости: настройки, сессия БД, сервисы, проверка токенов."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import ADMIN_TOKEN_HEADER, SERVICE_TOKEN_HEADER
from app.core.security import tokens_match
from app.db.session import Database
from app.services.broadcast_service import BroadcastService
from app.services.event_service import EventService
from app.services.outbox_service import OutboxService
from app.services.stats_service import StatsService
from app.services.user_service import UserService


def get_settings(request: Request) -> Settings:
    """Настройки, созданные в create_app()."""
    settings: Settings = request.app.state.settings
    return settings


def get_database(request: Request) -> Database:
    """Движок БД, созданный в create_app()."""
    database: Database = request.app.state.database
    return database


SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[Database, Depends(get_database)]


async def get_session(database: DatabaseDep) -> AsyncIterator[AsyncSession]:
    """Сессия на запрос. Commit/rollback выполняют сервисы; незавершённое откатывается при закрытии."""
    async with database.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _unauthorized(header_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Missing or invalid {header_name}",
    )


async def require_admin_token(
    settings: SettingsDep,
    token: Annotated[str | None, Header(alias=ADMIN_TOKEN_HEADER)] = None,
) -> None:
    """Пропускает запрос только с верным админским токеном."""
    if not tokens_match(token, settings.admin_token):
        raise _unauthorized(ADMIN_TOKEN_HEADER)


async def require_service_token(
    settings: SettingsDep,
    token: Annotated[str | None, Header(alias=SERVICE_TOKEN_HEADER)] = None,
) -> None:
    """Пропускает запрос только с верным сервисным токеном (его знает бот-клиент)."""
    if not tokens_match(token, settings.service_token):
        raise _unauthorized(SERVICE_TOKEN_HEADER)


def get_event_service(session: SessionDep, settings: SettingsDep) -> EventService:
    """Сервис обработки событий."""
    return EventService(session, settings=settings)


def get_outbox_service(session: SessionDep, settings: SettingsDep) -> OutboxService:
    """Сервис выдачи и подтверждения outbox."""
    return OutboxService(session, settings=settings)


def get_stats_service(session: SessionDep) -> StatsService:
    """Сервис статистики."""
    return StatsService(session)


def get_user_service(session: SessionDep, settings: SettingsDep) -> UserService:
    """Сервис карточки пользователя."""
    return UserService(session, default_tz_offset_minutes=settings.default_tz_offset_minutes)


def get_broadcast_service(session: SessionDep) -> BroadcastService:
    """Сервис рассылки."""
    return BroadcastService(session)


EventServiceDep = Annotated[EventService, Depends(get_event_service)]
OutboxServiceDep = Annotated[OutboxService, Depends(get_outbox_service)]
StatsServiceDep = Annotated[StatsService, Depends(get_stats_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
BroadcastServiceDep = Annotated[BroadcastService, Depends(get_broadcast_service)]