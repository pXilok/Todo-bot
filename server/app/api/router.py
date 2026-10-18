"""Сборка роутеров версии API. Префикс добавляется в create_app()."""

from fastapi import APIRouter

from app.api import admin, events, outbox, stats, users

api_router = APIRouter()
api_router.include_router(events.router)
api_router.include_router(users.router)
api_router.include_router(stats.router)
api_router.include_router(admin.router)
api_router.include_router(outbox.router)