import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

DOCUMENT = {"title": "Utility bill", "content": "Electricity utility bill for March 2026."}


async def test_create_document_returns_201(
    client: AsyncClient, created_client: dict[str, object]
) -> None:
    response = await client.post(f"/clients/{created_client['id']}/documents", json=DOCUMENT)

    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["id"]).version == 7
    assert body["client_id"] == created_client["id"]
    assert body["title"] == DOCUMENT["title"]
    assert body["content"] == DOCUMENT["content"]
    assert body["created_at"]
    assert body["summary_status"] == "pending"
    assert body["summary"] is None


async def test_long_document_is_chunked_and_embedded(
    client: AsyncClient, created_client: dict[str, object], db: AsyncEngine
) -> None:
    content = " ".join(f"word{i}" for i in range(400))

    response = await client.post(
        f"/clients/{created_client['id']}/documents", json={"title": "Long", "content": content}
    )

    async with db.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT chunk_index, vector_dims(embedding) FROM document_chunks "
                    "WHERE document_id = :id ORDER BY chunk_index"
                ),
                {"id": response.json()["id"]},
            )
        ).all()
    assert [r[0] for r in rows] == [0, 1, 2, 3]  # 400 words, windows of 150 with 30 overlap
    assert {r[1] for r in rows} == {384}


async def test_unknown_client_returns_404(client: AsyncClient) -> None:
    response = await client.post(f"/clients/{uuid.uuid7()}/documents", json=DOCUMENT)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


async def test_malformed_client_id_returns_422(client: AsyncClient) -> None:
    response = await client.post("/clients/not-a-uuid/documents", json=DOCUMENT)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "No content"},
        {"content": "No title"},
        {"title": "Blank", "content": "   "},
        {"title": "", "content": "text"},
        {"title": "Too long", "content": "x" * 100_001},
    ],
)
async def test_invalid_document_returns_422(
    client: AsyncClient, created_client: dict[str, object], payload: dict[str, str]
) -> None:
    response = await client.post(f"/clients/{created_client['id']}/documents", json=payload)

    assert response.status_code == 422
