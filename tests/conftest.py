from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _fresh_settings() -> None:
    # Settings are cached; tests that change env vars need a clean read.
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    # httpx's ASGITransport does not run lifespan events, so run them explicitly.
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c,
    ):
        yield c
