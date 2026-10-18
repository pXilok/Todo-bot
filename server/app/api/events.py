"""POST /api/v1/events."""

from fastapi import APIRouter, Depends, status

from app.api.deps import EventServiceDep, require_service_token
from app.schemas.events import EventResponse, NormalizedEvent

router = APIRouter(
    tags=["events"],
    dependencies=[Depends(require_service_token)],
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Неверный X-Service-Token"}},
)


@router.post(
    "/events",
    response_model=EventResponse,
    summary="Принять нормализованное событие",
)
async def receive_event(event: NormalizedEvent, service: EventServiceDep) -> EventResponse:
    """Обрабатывает событие и возвращает действия для клиента.

    Повторная доставка того же (platform, update_id) даёт пустой actions и duplicate=true.
    """
    return await service.handle(event)