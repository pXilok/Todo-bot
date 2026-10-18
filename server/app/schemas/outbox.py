"""Схемы протокола outbox (claim/ack) между клиентом и сервером."""

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from app.core.constants import AckStatus, OutboxKind

MAX_ACK_BATCH = 500


class OutboxItemOut(BaseModel):
    """Сообщение, которое клиент должен доставить."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    kind: OutboxKind
    text: str


class OutboxClaimResponse(BaseModel):
    """Пачка сообщений к доставке."""

    items: list[OutboxItemOut]


class OutboxAckItem(BaseModel):
    """Результат доставки одного сообщения."""

    model_config = ConfigDict(extra="forbid")

    id: PositiveInt
    status: AckStatus
    error: str | None = Field(default=None, max_length=500)


class OutboxAckRequest(BaseModel):
    """Подтверждение доставки пачки сообщений."""

    model_config = ConfigDict(extra="forbid")

    items: list[OutboxAckItem] = Field(min_length=1, max_length=MAX_ACK_BATCH)


class OutboxAckResponse(BaseModel):
    """Количество обновлённых записей."""

    updated: int