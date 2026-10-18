"""POST /api/v1/outbox/claim и /api/v1/outbox/ack."""

from fastapi import APIRouter, Depends, status

from app.api.deps import OutboxServiceDep, require_service_token
from app.schemas.outbox import OutboxAckRequest, OutboxAckResponse, OutboxClaimResponse

router = APIRouter(
    prefix="/outbox",
    tags=["outbox"],
    dependencies=[Depends(require_service_token)],
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Неверный X-Service-Token"}},
)


@router.post(
    "/claim",
    response_model=OutboxClaimResponse,
    summary="Забрать сообщения к доставке",
)
async def claim(service: OutboxServiceDep) -> OutboxClaimResponse:
    """Создаёт напоминания по наступившим задачам и отдаёт пачку pending-записей."""
    return await service.claim()


@router.post(
    "/ack",
    response_model=OutboxAckResponse,
    summary="Подтвердить доставку",
)
async def ack(payload: OutboxAckRequest, service: OutboxServiceDep) -> OutboxAckResponse:
    """Отмечает записи как sent или failed."""
    return await service.ack(payload)