import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings
from app.main import create_app
from app.repositories.synonyms import SynonymRepository
from tests.helpers import Hits, Search

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
        await conn.execute(text("TRUNCATE clients, documents, document_search_chunks CASCADE"))
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


@pytest.fixture
def api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Turn API key auth on for the test; returns the key to send in X-API-Key."""
    monkeypatch.setenv("API_KEY", "s3cret")
    return "s3cret"


@pytest.fixture
async def synonyms(db: AsyncEngine) -> AsyncIterator[SynonymRepository]:
    async with AsyncSession(db) as session:
        yield SynonymRepository(session)


# --- Search ------------------------------------------------------------------------------------

SEARCH_CLIENTS = [
    {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@neviswealth.com",
        "description": "Retired engineer focused on capital preservation.",
    },
    {"first_name": "Maria", "last_name": "Garcia", "email": "maria@example.org"},
]

# title -> content, attached to the first client
SEARCH_DOCUMENTS = {
    "Utility bill": "Electricity utility bill for March 2026 issued to John Doe, 12 Baker Street.",
    "Passport copy": "Scanned copy of passport, nationality British, date of birth 01.02.1980.",
    "Portfolio review": "Quarterly review of equity and bond allocation with rebalancing advice.",
    "Wire instructions": "Transfer funds to IBAN DE89370400440532013000 before the end of month.",
}


@pytest.fixture
async def corpus(client: AsyncClient) -> dict[str, str]:
    """Creates SEARCH_CLIENTS and SEARCH_DOCUMENTS; returns {email or title: id}."""
    ids: dict[str, str] = {}
    for payload in SEARCH_CLIENTS:
        response = await client.post("/clients", json=payload)
        assert response.status_code == 201
        ids[payload["email"]] = response.json()["id"]
    owner = ids[SEARCH_CLIENTS[0]["email"]]
    for title, content in SEARCH_DOCUMENTS.items():
        response = await client.post(
            f"/clients/{owner}/documents", json={"title": title, "content": content}
        )
        assert response.status_code == 201
        ids[title] = response.json()["id"]
    return ids


@pytest.fixture
def search(client: AsyncClient) -> Search:
    """`await search("address proof")` -> the /search response body (asserts 200)."""

    async def run(q: str) -> Hits:
        response = await client.get("/search", params={"q": q})
        assert response.status_code == 200, response.text
        hits: Hits = response.json()
        return hits

    return run
