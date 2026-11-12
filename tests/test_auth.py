import pytest
from httpx import AsyncClient

CLIENT = {"first_name": "Ann", "last_name": "Lee", "email": "ann@example.com"}

pytestmark = pytest.mark.usefixtures("api_key")


async def test_missing_key_returns_401(client: AsyncClient) -> None:
    response = await client.post("/clients", json=CLIENT)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "APIKey"


async def test_wrong_key_returns_401(client: AsyncClient) -> None:
    response = await client.post("/clients", json=CLIENT, headers={"X-API-Key": "nope"})

    assert response.status_code == 401


async def test_valid_key_is_accepted(client: AsyncClient, api_key: str) -> None:
    response = await client.post("/clients", json=CLIENT, headers={"X-API-Key": api_key})

    assert response.status_code == 201


async def test_health_and_docs_stay_public(client: AsyncClient) -> None:
    assert (await client.get("/health")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


async def test_search_requires_key(client: AsyncClient) -> None:
    assert (await client.get("/search", params={"q": "x"})).status_code == 401
