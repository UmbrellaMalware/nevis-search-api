import pytest
from httpx import AsyncClient

CLIENT = {"first_name": "Ann", "last_name": "Lee", "email": "ann@example.com"}


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "s3cret")


async def test_missing_key_returns_401(client: AsyncClient) -> None:
    response = await client.post("/clients", json=CLIENT)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "APIKey"


async def test_wrong_key_returns_401(client: AsyncClient) -> None:
    response = await client.post("/clients", json=CLIENT, headers={"X-API-Key": "nope"})

    assert response.status_code == 401


async def test_valid_key_is_accepted(client: AsyncClient) -> None:
    response = await client.post("/clients", json=CLIENT, headers={"X-API-Key": "s3cret"})

    assert response.status_code == 201


async def test_health_and_docs_stay_public(client: AsyncClient) -> None:
    assert (await client.get("/health")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


async def test_search_requires_key(client: AsyncClient) -> None:
    assert (await client.get("/search", params={"q": "x"})).status_code == 401
