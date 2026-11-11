import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, Text, func, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentSearchChunk

FTS_CONFIG = "english"


@dataclass(frozen=True, slots=True)
class DocumentMatch:
    document: Document
    snippet: str  # content of the best-matching chunk
    score: float  # cosine similarity (semantic) or ts_rank_cd (full-text)


class DocumentRepository:
    """Data access for documents. Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> Document:
        """Persist a document together with its search chunks (cascaded by the relationship)."""
        self._session.add(document)
        await self._session.flush()
        return document

    async def search_semantic(
        self, vectors: Sequence[list[float]], min_similarity: float, limit: int
    ) -> list[DocumentMatch]:
        """Documents whose best chunk is close to any query vector (max similarity wins)."""
        candidates = limit * 5  # several chunks may belong to the same document
        # HNSW returns at most ef_search rows; make sure it can serve all candidates.
        await self._session.execute(text(f"SET LOCAL hnsw.ef_search = {int(candidates)}"))

        best: dict[uuid.UUID, tuple[str, float]] = {}
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
                if document_id not in best or similarity > best[document_id][1]:
                    best[document_id] = (content, similarity)
        return await self._load(best, limit)

    async def search_full_text(
        self, query: str, phrases: Sequence[str], limit: int
    ) -> list[DocumentMatch]:
        """Postgres full-text match of the query (web-search syntax) OR any expansion phrase."""
        tsquery: ColumnElement[Any] = func.websearch_to_tsquery(FTS_CONFIG, literal(query, Text))
        for phrase in phrases:
            tsquery = tsquery.op("||")(func.phraseto_tsquery(FTS_CONFIG, literal(phrase, Text)))
        rank = func.ts_rank_cd(DocumentSearchChunk.search_tsv, tsquery)

        rows = await self._session.execute(
            select(DocumentSearchChunk.document_id, DocumentSearchChunk.content, rank)
            .where(DocumentSearchChunk.search_tsv.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(limit * 5)
        )
        best: dict[uuid.UUID, tuple[str, float]] = {}
        for document_id, content, score in rows:
            if document_id not in best:  # rows are ordered by rank
                best[document_id] = (content, float(score))
        return await self._load(best, limit)

    async def _load(
        self, best: dict[uuid.UUID, tuple[str, float]], limit: int
    ) -> list[DocumentMatch]:
        top = sorted(best.items(), key=lambda item: item[1][1], reverse=True)[:limit]
        if not top:
            return []
        documents = await self._session.scalars(
            select(Document).where(Document.id.in_([doc_id for doc_id, _ in top]))
        )
        by_id = {doc.id: doc for doc in documents}
        return [
            DocumentMatch(document=by_id[doc_id], snippet=snippet, score=score)
            for doc_id, (snippet, score) in top
            if doc_id in by_id
        ]
