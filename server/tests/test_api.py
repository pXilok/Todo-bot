"""Базовые проверки: здоровье сервера, /start, идемпотентность, токены."""

import os

from httpx import AsyncClient

EVENTS_URL = "/api/v1/events"
STATS_URL = "/api/v1/stats"


def service_headers() -> dict[str, str]:
    return {"X-Service-Token": os.environ["SERVICE_TOKEN"]}


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": os.environ["ADMIN_TOKEN"]}


def make_event(update_id: int, text: str = "/start", user_id: int = 42) -> dict[str, object]:
    return {
        "platform": "telegram",
        "update_id": update_id,
        "user": {"id": user_id, "username": "demo", "first_name": "Demo"},
        "chat_id": user_id,
        "message_id": 10,
        "type": "message",
        "text": text,
        "callback_data": None,
        "timestamp": "2026-10-18T10:00:00+00:00",
    }


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200


async def test_start_returns_actions(client: AsyncClient) -> None:
    response = await client.post(EVENTS_URL, json=make_event(1001), headers=service_headers())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["actions"], "на /start должны прийти действия"
    assert body["state"] == "MAIN_MENU"
    assert body["duplicate"] is False


async def test_duplicate_update_is_ignored(client: AsyncClient) -> None:
    first = await client.post(EVENTS_URL, json=make_event(1002), headers=service_headers())
    second = await client.post(EVENTS_URL, json=make_event(1002), headers=service_headers())

    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert second.json()["actions"] == []


async def test_events_require_service_token(client: AsyncClient) -> None:
    # 401 — ожидаемый ответ; 422 тоже допустим, если заголовок объявлен обязательным.
    response = await client.post(EVENTS_URL, json=make_event(1003))

    assert response.status_code in (401, 422)


async def test_stats_require_admin_token(client: AsyncClient) -> None:
    without_token = await client.get(STATS_URL)
    with_token = await client.get(STATS_URL, headers=admin_headers())

    assert without_token.status_code in (401, 422)
    assert with_token.status_code == 200