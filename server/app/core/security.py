"""Примитивы проверки токенов. FastAPI-зависимости лежат в api/deps.py."""

import secrets

from pydantic import SecretStr


def tokens_match(provided: str | None, expected: SecretStr) -> bool:
    """Сравнивает токены за постоянное время, чтобы исключить timing-атаки."""
    if not provided:
        return False
    return secrets.compare_digest(
        provided.encode("utf-8"),
        expected.get_secret_value().encode("utf-8"),
    )