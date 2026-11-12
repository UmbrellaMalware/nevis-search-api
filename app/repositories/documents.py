import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, Text, func, literal, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.exceptions import DocumentAlreadyExistsError
from app.models import Document, DocumentSearchChunk, SummaryStatus
from app.repositories.constraints import violated_constraint
from app.utils.best_scores import BestScores

FTS_CONFIG = "english"
CONTENT_HASH_UNIQUE_INDEX = "uq_documents_client_content_hash"


@dataclass(frozen=True, slots=True)
class DocumentMatch:
    document: Document
    snippet: str  # content of the best-matching chunk
    score: float  # cosine similarity (semantic) or ts_rank_cd (full-text)


class DocumentRepository:
    """Data access for documents. Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, document_id: uuid.UUID) -> Document | None:
        return await self._session.get(Document, document_id)

    async def lock_next_pending_summary(self) -> Document | None:
        """The oldest document still waiting for a summary, locked until the transaction ends.

        `FOR UPDATE SKIP LOCKED` lets several workers run side by side: each takes a different
        document, none waits for another. If a worker dies, its transaction is rolled back, the
        lock is released and the document is picked up again.
        """
        return await self._session.scalar(
            select(Document)
            .where(Document.summary_status == SummaryStatus.PENDING)
            .order_by(Document.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )

    async def find_id_by_content_hash(
        self, client_id: uuid.UUID, content_hash: bytes
    ) -> uuid.UUID | None:
        """Id of the client's document with this content hash, if one was already uploaded."""
        return await self._session.scalar(
            select(Document.id).where(
                Document.client_id == client_id, Document.content_hash == content_hash
            )
        )

    async def add(self, document: Document) -> Document:
        """Persist a document together with its search chunks (cascaded by the relationship).

        Raises DocumentAlreadyExistsError if the client already has a document with the same
        content: the unique index catches two concurrent uploads of the same document.
        The savepoint keeps the session usable after the failed insert, to look up the winner.
        """
        try:
            async with self._session.begin_nested():
                self._session.add(document)
        except IntegrityError as exc:
            if violated_constraint(exc) != CONTENT_HASH_UNIQUE_INDEX:
                raise
            existing = await self.find_id_by_content_hash(
                document.client_id, document.content_hash
            )
            if existing is None:
                raise
            raise DocumentAlreadyExistsError(document.client_id, existing) from exc
        return document

    async def search_semantic(
        self, vectors: Sequence[list[float]], min_similarity: float, limit: int
    ) -> list[DocumentMatch]:
        """Documents whose best chunk is close to any query vector (max similarity wins)."""
        # shortcut: one long document (up to ~120 chunks) can fill all candidates and hide other
        # documents; fetch more chunks until enough documents are found when that bites.
        candidates = limit * 5  # several chunks may belong to the same document
        # HNSW returns at most ef_search rows; make sure it can serve all candidates.
        await self._session.execute(text(f"SET LOCAL hnsw.ef_search = {int(candidates)}"))

        best: BestScores[uuid.UUID, str] = BestScores()  # document id -> best chunk's content
        for vector in vectors:
            distance = DocumentSearchChunk.embedding.cosine_distance(vector)
            rows = await self._session.execute(
                select(DocumentSearchChunk.document_id, DocumentSearchChunk.content, distance)
                .order_by(distance)
                .limit(candidates)
            )
            for document_id, content, dist in rows:
                similarity = 1 - float(dist)
                if similarity < min_similarity:
                    break  # rows are ordered by distance
                best.offer(document_id, content, similarity)
        return await self._load(best.top(limit))

    async def search_full_text(
        self, query: str, phrases: Sequence[str], limit: int
    ) -> list[DocumentMatch]:
        """Postgres full-text match of the query (web-search syntax) OR any expansion phrase."""
        tsquery: ColumnElement[Any] = func.websearch_to_tsquery(FTS_CONFIG, literal(query, Text))
        for phrase in phrases:
            tsquery = tsquery.op("||")(func.phraseto_tsquery(FTS_CONFIG, literal(phrase, Text)))
        # Postgres "text search rank, cover density": higher when the matched words occur
        # often and close together in the chunk ("utility bill" beats "utility ... bill").
        rank = func.ts_rank_cd(DocumentSearchChunk.search_tsv, tsquery)

        rows = await self._session.execute(
            select(DocumentSearchChunk.document_id, DocumentSearchChunk.content, rank)
            .where(DocumentSearchChunk.search_tsv.op("@@")(tsquery))
            .order_by(rank.desc())
            # shortcut: same limit and same crowding problem as search_semantic.
            .limit(limit * 5)
        )
        best: BestScores[uuid.UUID, str] = BestScores()  # document id -> best chunk's content
        for document_id, content, score in rows:
            best.offer(document_id, content, float(score))
        return await self._load(best.top(limit))

    async def _load(self, top: list[tuple[uuid.UUID, str, float]]) -> list[DocumentMatch]:
        """Fetch the documents for `(document id, snippet, score)` rows, keeping their order.

        Without `content` (up to 100k characters each): search results never show it.
        """
        if not top:
            return []
        documents = await self._session.scalars(
            select(Document)
            .where(Document.id.in_([doc_id for doc_id, _, _ in top]))
            .options(defer(Document.content))
        )
        by_id = {doc.id: doc for doc in documents}
        return [
            DocumentMatch(document=by_id[doc_id], snippet=snippet, score=score)
            for doc_id, snippet, score in top
            if doc_id in by_id
        ]
