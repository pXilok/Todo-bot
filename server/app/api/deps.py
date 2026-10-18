"""Зависимости FastAPI: настройки, сессия БД, сервисы, проверка токенов."""

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
    return request.app.state.settings


def get_database(request: Request) -> Database:
    return request.app.state.database


SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[Database, Depends(get_database)]


async def get_session(database: DatabaseDep) -> AsyncIterator[AsyncSession]:
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
    if not tokens_match(token, settings.admin_token):
        raise _unauthorized(ADMIN_TOKEN_HEADER)


async def require_service_token(
    settings: SettingsDep,
    token: Annotated[str | None, Header(alias=SERVICE_TOKEN_HEADER)] = None,
) -> None:
    if not tokens_match(token, settings.service_token):
        raise _unauthorized(SERVICE_TOKEN_HEADER)


def get_event_service(session: SessionDep, settings: SettingsDep) -> EventService:
    return EventService(session, settings=settings)


def get_outbox_service(session: SessionDep, settings: SettingsDep) -> OutboxService:
    return OutboxService(session, settings=settings)


def get_stats_service(session: SessionDep) -> StatsService:
    return StatsService(session)


def get_user_service(session: SessionDep, settings: SettingsDep) -> UserService:
    return UserService(session, default_tz_offset_minutes=settings.default_tz_offset_minutes)


def get_broadcast_service(session: SessionDep) -> BroadcastService:
    return BroadcastService(session)


EventServiceDep = Annotated[EventService, Depends(get_event_service)]
OutboxServiceDep = Annotated[OutboxService, Depends(get_outbox_service)]
StatsServiceDep = Annotated[StatsService, Depends(get_stats_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
BroadcastServiceDep = Annotated[BroadcastService, Depends(get_broadcast_service)]