import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import create_app


async def test_health_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_reports_unreachable_database(monkeypatch: pytest.MonkeyPatch) -> None:
    # Port 1 on localhost: nothing listens there, so the connection is refused immediately.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:1/none")
    get_settings.cache_clear()
    app = create_app()

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}
