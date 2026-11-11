import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings
from app.main import create_app

ROOT = Path(__file__).resolve().parent.parent
# Captured once: some tests point the app at a broken URL, cleanup must still hit the real DB.
TEST_DATABASE_URL = os.environ.get("DATABASE_URL", Settings().database_url)


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    """Apply real Alembic migrations once, so the migrations themselves are under test."""
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
def _fresh_settings() -> None:
    # Settings are cached; tests that change env vars need a clean read.
    get_settings.cache_clear()


@pytest.fixture
async def db() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    yield
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE clients, documents, document_chunks CASCADE"))
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    # httpx's ASGITransport does not run lifespan events, so run them explicitly.
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c,
    ):
        yield c


@pytest.fixture
async def created_client(client: AsyncClient) -> dict[str, object]:
    response = await client.post(
        "/clients",
        json={"first_name": "John", "last_name": "Doe", "email": "john.doe@neviswealth.com"},
    )
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body
