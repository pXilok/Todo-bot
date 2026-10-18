"""Общие настройки тестов: временная база, миграции и HTTP-клиент без сети."""

import os
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

SERVER_DIR = Path(__file__).resolve().parents[1]
TEST_DIR = tempfile.mkdtemp(prefix="todo-bot-tests-")
DB_FILE = Path(TEST_DIR, "test.db").as_posix()

# Переменные окружения задаём до создания приложения, чтобы не трогать bot.db.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_FILE}"
os.environ["ADMIN_TOKEN"] = "test-admin-token-1234567890"
os.environ["SERVICE_TOKEN"] = "test-service-token-1234567890"


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Создаёт пустую временную базу по миграциям перед всеми тестами."""
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=SERVER_DIR,
        check=True,
        env=os.environ.copy(),
    )


@pytest_asyncio.fixture
async def client(migrated_database: None) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент, который обращается к приложению напрямую, без реальной сети."""
    from app.main import create_app

    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac