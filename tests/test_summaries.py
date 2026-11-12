import uuid

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.repositories.documents import DocumentRepository
from app.services.summaries import Summarizer, summarize_next
from tests.helpers import FailingSummarizer, FakeSummarizer


async def _get_summary(client: AsyncClient, document_id: object) -> dict[str, object]:
    response = await client.get(f"/documents/{document_id}/summary")
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


async def _request_summary(client: AsyncClient, document_id: object) -> Response:
    return await client.post(f"/documents/{document_id}/summary")


async def _run_worker_once(db: AsyncEngine, summarizer: Summarizer) -> bool:
    async with AsyncSession(db) as session:
        return await summarize_next(session, summarizer)


async def test_new_document_summary_is_not_requested(
    client: AsyncClient, created_document: dict[str, object], db: AsyncEngine
) -> None:
    assert await _get_summary(client, created_document["id"]) == {
        "document_id": created_document["id"],
        "status": "not_requested",
        "summary": None,
        "error": None,
    }
    # Nothing is queued until someone asks for it.
    assert await _run_worker_once(db, FakeSummarizer()) is False


async def test_request_then_poll_until_ready(
    client: AsyncClient, created_document: dict[str, object], db: AsyncEngine
) -> None:
    summarizer = FakeSummarizer("March electricity bill, EUR 84.20.")

    response = await _request_summary(client, created_document["id"])
    assert response.status_code == 202
    assert response.json()["status"] == "pending"

    assert await _run_worker_once(db, summarizer) is True
    assert summarizer.calls == [("Utility bill", "Electricity bill for March 2026, EUR 84.20.")]
    summary = await _get_summary(client, created_document["id"])
    assert summary["status"] == "ready"
    assert summary["summary"] == "March electricity bill, EUR 84.20."


async def test_requesting_a_ready_summary_returns_it_without_a_new_job(
    client: AsyncClient, created_document: dict[str, object], db: AsyncEngine
) -> None:
    await _request_summary(client, created_document["id"])
    await _run_worker_once(db, FakeSummarizer("Done."))

    response = await _request_summary(client, created_document["id"])

    assert response.status_code == 200
    assert response.json()["summary"] == "Done."
    assert await _run_worker_once(db, FakeSummarizer()) is False


async def test_requesting_twice_while_pending_queues_one_job(
    client: AsyncClient, created_document: dict[str, object], db: AsyncEngine
) -> None:
    await _request_summary(client, created_document["id"])
    assert (await _request_summary(client, created_document["id"])).status_code == 202

    summarizer = FakeSummarizer()
    await _run_worker_once(db, summarizer)
    await _run_worker_once(db, summarizer)
    assert len(summarizer.calls) == 1


async def test_llm_error_marks_failed_and_a_new_request_retries(
    client: AsyncClient, created_document: dict[str, object], db: AsyncEngine
) -> None:
    await _request_summary(client, created_document["id"])
    await _run_worker_once(db, FailingSummarizer())

    failed = await _get_summary(client, created_document["id"])
    assert failed["status"] == "failed"
    assert failed["error"] == "OpenAI is unavailable"

    retry = await _request_summary(client, created_document["id"])
    assert retry.status_code == 202
    assert retry.json() == {**failed, "status": "pending", "error": None}
    assert await _run_worker_once(db, FakeSummarizer()) is True


async def test_document_locked_by_another_worker_is_skipped(
    client: AsyncClient, created_document: dict[str, object], db: AsyncEngine
) -> None:
    await _request_summary(client, created_document["id"])
    async with AsyncSession(db) as first, AsyncSession(db) as second:
        locked = await DocumentRepository(first).lock_next_pending_summary()
        assert locked is not None

        # While the first worker holds the only pending document, the second finds nothing.
        assert await summarize_next(second, FakeSummarizer()) is False


async def test_unknown_document_returns_404(client: AsyncClient) -> None:
    unknown = uuid.uuid7()

    assert (await client.get(f"/documents/{unknown}/summary")).status_code == 404
    assert (await _request_summary(client, unknown)).status_code == 404
