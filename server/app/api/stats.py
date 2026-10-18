"""GET /api/v1/stats."""

from fastapi import APIRouter, Depends, status

from app.api.deps import StatsServiceDep, require_admin_token
from app.schemas.stats import StatsOut

router = APIRouter(
    tags=["stats"],
    dependencies=[Depends(require_admin_token)],
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Неверный X-Admin-Token"}},
)


@router.get("/stats", response_model=StatsOut, summary="Общая статистика")
async def get_stats(service: StatsServiceDep) -> StatsOut:
    """Агрегированные метрики по пользователям, задачам и сообщениям."""
    return await service.collect()