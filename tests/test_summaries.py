import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.repositories.documents import DocumentRepository
from app.services.summaries import summarize_next
from tests.helpers import FailingSummarizer, FakeSummarizer


async def _summary(client: AsyncClient, document_id: object) -> dict[str, object]:
    response = await client.get(f"/documents/{document_id}/summary")
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


async def test_new_document_summary_is_pending(
    client: AsyncClient, created_document: dict[str, object]
) -> None:
    assert await _summary(client, created_document["id"]) == {
        "document_id": created_document["id"],
        "status": "pending",
        "summary": None,
        "error": None,
    }


async def test_worker_stores_the_summary(
    client: AsyncClient, created_document: dict[str, object], db: AsyncEngine
) -> None:
    summarizer = FakeSummarizer("March electricity bill, EUR 84.20.")

    async with AsyncSession(db) as session:
        assert await summarize_next(session, summarizer) is True

    assert summarizer.calls == [("Utility bill", "Electricity bill for March 2026, EUR 84.20.")]
    summary = await _summary(client, created_document["id"])
    assert summary["status"] == "ready"
    assert summary["summary"] == "March electricity bill, EUR 84.20."


async def test_llm_error_marks_summary_failed(
    client: AsyncClient, created_document: dict[str, object], db: AsyncEngine
) -> None:
    async with AsyncSession(db) as session:
        assert await summarize_next(session, FailingSummarizer()) is True

    summary = await _summary(client, created_document["id"])
    assert summary["status"] == "failed"
    assert summary["error"] == "OpenAI is unavailable"


async def test_summarised_document_is_not_taken_again(
    created_document: dict[str, object], db: AsyncEngine
) -> None:
    summarizer = FakeSummarizer()
    async with AsyncSession(db) as session:
        await summarize_next(session, summarizer)
        assert await summarize_next(session, summarizer) is False

    assert len(summarizer.calls) == 1


async def test_document_locked_by_another_worker_is_skipped(
    created_document: dict[str, object], db: AsyncEngine
) -> None:
    async with AsyncSession(db) as first, AsyncSession(db) as second:
        locked = await DocumentRepository(first).lock_next_pending_summary()
        assert locked is not None

        # While the first worker holds the only pending document, the second finds nothing.
        assert await summarize_next(second, FakeSummarizer()) is False


async def test_empty_queue_returns_false(db: AsyncEngine) -> None:
    async with AsyncSession(db) as session:
        assert await summarize_next(session, FakeSummarizer()) is False


async def test_unknown_document_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/documents/{uuid.uuid7()}/summary")

    assert response.status_code == 404
