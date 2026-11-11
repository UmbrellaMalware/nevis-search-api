import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

VALID_CLIENT = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@neviswealth.com",
    "description": "Long-term investor focused on retirement planning.",
    "social_links": ["https://linkedin.com/in/johndoe"],
}


async def test_create_client_returns_201_with_full_resource(client: AsyncClient) -> None:
    response = await client.post("/clients", json=VALID_CLIENT)

    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["id"]).version == 7
    assert {k: body[k] for k in VALID_CLIENT} == VALID_CLIENT
    assert body["created_at"]


async def test_optional_fields_default(client: AsyncClient) -> None:
    response = await client.post(
        "/clients", json={"first_name": "Ann", "last_name": "Lee", "email": "ann@example.com"}
    )

    assert response.status_code == 201
    assert response.json()["description"] is None
    assert response.json()["social_links"] == []


async def test_description_is_embedded(client: AsyncClient, db: AsyncEngine) -> None:
    response = await client.post("/clients", json=VALID_CLIENT)

    async with db.connect() as conn:
        dims = await conn.scalar(
            text("SELECT vector_dims(description_embedding) FROM clients WHERE id = :id"),
            {"id": response.json()["id"]},
        )
    assert dims == 384


async def test_duplicate_email_is_rejected_case_insensitively(client: AsyncClient) -> None:
    assert (await client.post("/clients", json=VALID_CLIENT)).status_code == 201

    duplicate = {**VALID_CLIENT, "email": "John.Doe@NevisWealth.com"}
    response = await client.post("/clients", json=duplicate)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.parametrize(
    "patch",
    [
        {"email": "not-an-email"},
        {"first_name": ""},
        {"first_name": "   "},
        {"last_name": None},
        {"social_links": "https://not-a-list.com"},
    ],
)
async def test_invalid_payload_returns_422(client: AsyncClient, patch: dict[str, object]) -> None:
    response = await client.post("/clients", json={**VALID_CLIENT, **patch})

    assert response.status_code == 422


@pytest.mark.parametrize("missing", ["first_name", "last_name", "email"])
async def test_missing_required_field_returns_422(client: AsyncClient, missing: str) -> None:
    payload = {k: v for k, v in VALID_CLIENT.items() if k != missing}

    response = await client.post("/clients", json=payload)

    assert response.status_code == 422
