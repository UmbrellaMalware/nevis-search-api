"""Document summaries: requested through the API, generated in the background by app/worker.py.

Postgres is the job queue. A new document is not_requested; a request makes it pending; the
worker takes the oldest pending one, asks the LLM for a summary and stores it as ready, or
stores the error as failed (one attempt; a new request tries again).
"""

import logging
import uuid
from typing import Protocol

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DocumentNotFoundError
from app.models import Document, SummaryStatus
from app.repositories.documents import DocumentRepository
from app.services.dto import SummaryDTO

logger = logging.getLogger(__name__)

MAX_ERROR_CHARS = 1000

_INSTRUCTIONS = (
    "You summarise documents for a wealth-management advisor. Write 2-4 sentences in English: "
    "what the document is, who it concerns and the key facts (amounts, dates, obligations). "
    "Use only information from the document; do not add advice or assumptions."
)


class Summarizer(Protocol):
    async def summarize(self, title: str, content: str) -> str: ...


class OpenAISummarizer:
    def __init__(self, api_key: str, model: str) -> None:
        # The SDK's defaults (600 s timeout, 2 hidden retries) could hold the queue for ~30 min.
        self._client = AsyncOpenAI(api_key=api_key, timeout=60, max_retries=0)
        self._model = model

    async def summarize(self, title: str, content: str) -> str:
        response = await self._client.responses.create(
            model=self._model,
            instructions=_INSTRUCTIONS,
            input=f"Title: {title}\n\n{content}",
        )
        return response.output_text.strip()


async def summarize_next(session: AsyncSession, summarizer: Summarizer) -> bool:
    """Summarise the oldest pending document. Returns False if there was nothing to do.

    The document stays locked while the LLM works, so two workers never summarise the same one.
    """
    document = await DocumentRepository(session).lock_next_pending_summary()
    if document is None:
        await session.rollback()
        return False

    try:
        document.summary = await summarizer.summarize(document.title, document.content)
        document.summary_status = SummaryStatus.READY
        document.summary_error = None
    except Exception as exc:  # any LLM failure marks the summary failed instead of retrying
        logger.warning("Summary failed for document %s: %s", document.id, exc)
        document.summary_status = SummaryStatus.FAILED
        document.summary_error = str(exc)[:MAX_ERROR_CHARS] or type(exc).__name__
    await session.commit()
    return True


async def request_summary(session: AsyncSession, document_id: uuid.UUID) -> SummaryDTO:
    """Queue a summary for the worker. Raises DocumentNotFoundError for unknown ids.

    not_requested or failed -> pending (a failed summary is tried again);
    pending or ready        -> unchanged (no second LLM call for the same document).
    """
    document = await _get(session, document_id)
    if document.summary_status in (SummaryStatus.NOT_REQUESTED, SummaryStatus.FAILED):
        document.summary_status = SummaryStatus.PENDING
        document.summary_error = None
        await session.commit()
    return _to_dto(document)


async def get_summary(session: AsyncSession, document_id: uuid.UUID) -> SummaryDTO:
    """Current summary state of a document. Raises DocumentNotFoundError for unknown ids."""
    return _to_dto(await _get(session, document_id))


async def _get(session: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await DocumentRepository(session).get(document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)
    return document


def _to_dto(document: Document) -> SummaryDTO:
    return SummaryDTO(
        document_id=document.id,
        status=document.summary_status,
        summary=document.summary,
        error=document.summary_error,
    )
