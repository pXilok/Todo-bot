"""POST /api/v1/admin/broadcast."""

from fastapi import APIRouter, Depends, status

from app.api.deps import BroadcastServiceDep, require_admin_token
from app.schemas.admin import BroadcastRequest, BroadcastResponse

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Неверный X-Admin-Token"}},
)


@router.post(
    "/broadcast",
    response_model=BroadcastResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Рассылка всем пользователям",
)
async def broadcast(
    payload: BroadcastRequest,
    service: BroadcastServiceDep,
) -> BroadcastResponse:
    """Кладёт сообщение в outbox для каждого пользователя. Доставку выполняет бот-клиент."""
    return await service.broadcast(payload)