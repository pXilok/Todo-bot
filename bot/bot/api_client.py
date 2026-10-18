"""HTTP-клиент к серверу. Повторяет запрос только при сетевых сбоях."""

import asyncio
import logging
from typing import Any

import httpx

from bot.schemas import (
    EventResponse,
    NormalizedEvent,
    OutboxAckItem,
    OutboxClaimResponse,
    parse_event_response,
)

logger = logging.getLogger(__name__)

SERVICE_TOKEN_HEADER = "X-Service-Token"
EVENTS_PATH = "/api/v1/events"
OUTBOX_CLAIM_PATH = "/api/v1/outbox/claim"
OUTBOX_ACK_PATH = "/api/v1/outbox/ack"
RETRY_BASE_DELAY_SECONDS = 1.0


class ServerUnavailableError(Exception):
    """Сервер не ответил ни за одну попытку."""


class ServerRejectedError(Exception):
    """Сервер ответил ошибкой (например, 401 или 422). Повтор не поможет."""


class ApiClient:
    """Обёртка над httpx.

    Повтор безопасен: сервер отсекает дубли событий по update_id,
    а незавершённые записи outbox выдаются повторно по таймауту.
    """

    def __init__(
        self,
        base_url: str,
        service_token: str,
        *,
        timeout: float,
        retries: int,
    ) -> None:
        self._retries = retries
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={SERVICE_TOKEN_HEADER: service_token},
            timeout=httpx.Timeout(timeout),
            trust_env=False,
        )

    async def close(self) -> None:
        """Закрывает соединения."""
        await self._client.aclose()

    async def send_event(self, event: NormalizedEvent) -> EventResponse:
        """Отправляет событие и возвращает действия для выполнения."""
        data = await self._post(EVENTS_PATH, event.model_dump(mode="json"))
        return parse_event_response(data)

    async def claim_outbox(self) -> OutboxClaimResponse:
        """Забирает пачку сообщений к доставке."""
        data = await self._post(OUTBOX_CLAIM_PATH)
        return OutboxClaimResponse.model_validate(data)

    async def ack_outbox(self, items: list[OutboxAckItem]) -> None:
        """Подтверждает результаты доставки."""
        body = {"items": [item.model_dump(mode="json") for item in items]}
        await self._post(OUTBOX_ACK_PATH, body)

    async def _post(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(1, self._retries + 1):
            try:
                response = await self._client.post(path, json=body)
            except httpx.TransportError as exc:
                logger.warning(
                    "Server unreachable (attempt %s/%s) %s: %s",
                    attempt,
                    self._retries,
                    path,
                    exc,
                )
                if attempt < self._retries:
                    await asyncio.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
                continue

            if response.status_code >= 400:
                raise ServerRejectedError(
                    f"{path} -> {response.status_code}: {response.text[:300]}"
                )
            result: dict[str, Any] = response.json()
            return result

        raise ServerUnavailableError(f"{path}: no response after {self._retries} attempts")