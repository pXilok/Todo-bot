"""GET /health."""

import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.api.deps import SessionDep
from app.schemas.health import HealthOut

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthOut,
    summary="Проверка работоспособности",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthOut}},
)
async def health(response: Response, session: SessionDep) -> HealthOut:
    """Возвращает 200, если сервис и БД доступны, иначе 503."""
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Health check: database unavailable")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthOut(status="degraded", database="unavailable", version=__version__)
    return HealthOut(status="ok", database="ok", version=__version__)