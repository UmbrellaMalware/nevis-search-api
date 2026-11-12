"""Hybrid search across clients and documents.

Four independent retrievers each produce a ranked list:

* clients   / lexical   - substring + trigram match on email, full name, description
* clients   / semantic  - Sentence-BERT similarity of the client description
* documents / semantic  - Sentence-BERT similarity of the best chunk
* documents / full-text - Postgres full-text match on chunks

The query is first expanded with domain synonyms from the `search_synonyms` table (e.g.
"address proof" -> "utility bill", ...); semantic retrievers take the best similarity over the
query and its synonyms, full-text ORs the synonym phrases in.

The lists are merged with Reciprocal Rank Fusion: score = sum(1 / (k + rank)). RRF only uses
ranks, so trigram similarity, cosine similarity and ts_rank never have to be compared directly,
and an item found by several retrievers naturally rises to the top.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client
from app.repositories.clients import ClientRepository
from app.repositories.documents import DocumentMatch, DocumentRepository
from app.repositories.synonyms import SynonymRepository
from app.schemas import (
    ClientOut,
    ClientSearchHit,
    DocumentBrief,
    DocumentSearchHit,
    MatchType,
    SearchHit,
)
from app.services.embeddings import Embedder

RRF_K = 60
SNIPPET_CHARS = 300
MIN_LEXICAL_QUERY_CHARS = 2  # a single character would substring-match nearly everything


@dataclass
class _Fused:
    """One client or document accumulated across all retrievers (Reciprocal Rank Fusion).

    Retriever scores live on incomparable scales, so RRF uses ranks only: each retriever adds
    1 / (RRF_K + rank) to `score`. Items found by several retrievers sum up and rank higher.
    """

    score: float = 0.0
    matched_by: list[MatchType] = field(default_factory=list)
    client: Client | None = None
    match: DocumentMatch | None = None  # best document match seen so far


class _RankFusion:
    """Merges the ranked lists of all retrievers into one list with Reciprocal Rank Fusion.

    Example: a document ranked 1st by semantic search and 3rd by full-text search scores
    1/61 + 1/63 = 0.0323 and beats a document ranked 1st by semantic search only (1/61 = 0.0164).
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[str, uuid.UUID], _Fused] = {}

    def add_clients(self, clients: Iterable[Client], kind: MatchType) -> None:
        """Add one retriever's client list, best match first."""
        for rank, client in enumerate(clients, 1):
            self._add(("client", client.id), rank, kind).client = client

    def add_documents(self, matches: Iterable[DocumentMatch], kind: MatchType) -> None:
        """Add one retriever's document list, best match first.

        A document found by several retrievers keeps the snippet of the first one that found it.
        """
        for rank, match in enumerate(matches, 1):
            entry = self._add(("document", match.document.id), rank, kind)
            entry.match = entry.match or match

    def top(self, limit: int) -> list[_Fused]:
        """The `limit` entries with the highest fused score."""
        return sorted(self._entries.values(), key=lambda e: e.score, reverse=True)[:limit]

    def _add(self, key: tuple[str, uuid.UUID], rank: int, kind: MatchType) -> _Fused:
        entry = self._entries.setdefault(key, _Fused())
        entry.score += 1 / (RRF_K + rank)
        entry.matched_by.append(kind)
        return entry


async def _expand_and_embed(
    session: AsyncSession, embedder: Embedder, query: str
) -> tuple[list[str], list[list[float]]]:
    """Find glossary synonyms of the query and embed the query together with them.

    "address proof" -> (["utility bill", "bank statement", ...],
                        [vector("address proof"), vector("utility bill"), ...])
    "investment strategy" -> ([], [vector("investment strategy")])
    """
    synonyms = await SynonymRepository(session).expand(query)
    vectors = await embedder.embed([query, *synonyms])
    return synonyms, vectors


async def _search_clients(
    session: AsyncSession,
    fusion: _RankFusion,
    query: str,
    vectors: list[list[float]],
    *,
    min_similarity: float,
    limit: int,
) -> None:
    """Run both client retrievers and add their results to `fusion`.

    Lexical (email, name, description; substring + typos) is skipped for one-character queries,
    which would substring-match almost every client.
    """
    clients = ClientRepository(session)
    if len(query) >= MIN_LEXICAL_QUERY_CHARS:
        lexical = await clients.search_lexical(query, limit)
        fusion.add_clients((client for client, _ in lexical), MatchType.LEXICAL)
    semantic = await clients.search_semantic(vectors, min_similarity, limit)
    fusion.add_clients((client for client, _ in semantic), MatchType.SEMANTIC)


async def _search_documents(
    session: AsyncSession,
    fusion: _RankFusion,
    query: str,
    synonyms: list[str],
    vectors: list[list[float]],
    *,
    min_similarity: float,
    limit: int,
) -> None:
    """Run both document retrievers and add their results to `fusion`.

    Semantic first, so its snippet (the chunk closest in meaning) wins when both find a document.
    """
    documents = DocumentRepository(session)
    semantic = await documents.search_semantic(vectors, min_similarity, limit)
    fusion.add_documents(semantic, MatchType.SEMANTIC)
    full_text = await documents.search_full_text(query, synonyms, limit)
    fusion.add_documents(full_text, MatchType.FULL_TEXT)


def _snippet(text: str) -> str:
    """Shorten a matched chunk to at most SNIPPET_CHARS characters for the response.

    A chunk is up to 150 words (~1000 characters): too long to show in a result list.

    "Electricity bill for March"  -> "Electricity bill for March"  (fits: unchanged)
    <a 1000-character chunk>      -> <its first 299 characters, trailing whitespace stripped>
                                     + "…"  (so the result is at most 300 characters)
    """
    if len(text) <= SNIPPET_CHARS:
        return text
    return text[: SNIPPET_CHARS - 1].rstrip() + "…"


def _to_hit(entry: _Fused) -> SearchHit:
    """Turn a fused entry into the API response item: a client hit or a document hit."""
    score = round(entry.score, 6)
    if entry.client is not None:
        return ClientSearchHit(
            score=score,
            matched_by=entry.matched_by,
            client=ClientOut.model_validate(entry.client),
        )
    assert entry.match is not None  # every entry is added either as a client or as a document
    return DocumentSearchHit(
        score=score,
        matched_by=entry.matched_by,
        document=DocumentBrief.model_validate(entry.match.document),
        snippet=_snippet(entry.match.snippet),
    )


async def search(
    session: AsyncSession,
    embedder: Embedder,
    query: str,
    *,
    min_similarity: float,
    limit: int,
) -> list[SearchHit]:
    """Search clients and documents; return one list, best match first (at most `limit`)."""
    query = query.strip()
    synonyms, vectors = await _expand_and_embed(session, embedder, query)

    fusion = _RankFusion()
    await _search_clients(
        session, fusion, query, vectors, min_similarity=min_similarity, limit=limit
    )
    await _search_documents(
        session, fusion, query, synonyms, vectors, min_similarity=min_similarity, limit=limit
    )
    return [_to_hit(entry) for entry in fusion.top(limit)]
