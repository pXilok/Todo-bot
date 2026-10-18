"""GET /api/v1/users/{user_id}."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.deps import UserServiceDep, require_admin_token
from app.schemas.users import UserOut

router = APIRouter(
    tags=["users"],
    dependencies=[Depends(require_admin_token)],
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Неверный X-Admin-Token"}},
)


@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    summary="Информация о пользователе",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Пользователь не найден"}},
)
async def get_user(
    user_id: Annotated[int, Path(gt=0)],
    service: UserServiceDep,
) -> UserOut:
    """Карточка пользователя: профиль, состояние FSM, настройки, счётчики."""
    card = await service.get_card(user_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return card