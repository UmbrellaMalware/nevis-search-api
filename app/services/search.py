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


def _snippet(text: str) -> str:
    return text if len(text) <= SNIPPET_CHARS else text[: SNIPPET_CHARS - 1].rstrip() + "…"


async def search(
    session: AsyncSession,
    embedder: Embedder,
    query: str,
    *,
    min_similarity: float,
    limit: int,
) -> list[SearchHit]:
    query = query.strip()
    clients, documents = ClientRepository(session), DocumentRepository(session)

    synonyms = await SynonymRepository(session).expand(query)
    vectors = await embedder.embed([query, *synonyms])

    fused: dict[tuple[str, uuid.UUID], _Fused] = {}

    def add(key: tuple[str, uuid.UUID], rank: int, kind: MatchType) -> _Fused:
        entry = fused.setdefault(key, _Fused())
        entry.score += 1 / (RRF_K + rank)
        entry.matched_by.append(kind)
        return entry

    if len(query) >= MIN_LEXICAL_QUERY_CHARS:
        for rank, (client, _) in enumerate(await clients.search_lexical(query, limit), 1):
            add(("client", client.id), rank, MatchType.LEXICAL).client = client

    for rank, (client, _) in enumerate(
        await clients.search_semantic(vectors, min_similarity, limit), 1
    ):
        add(("client", client.id), rank, MatchType.SEMANTIC).client = client

    for kind, matches in (
        (MatchType.SEMANTIC, await documents.search_semantic(vectors, min_similarity, limit)),
        (MatchType.FULL_TEXT, await documents.search_full_text(query, synonyms, limit)),
    ):
        for rank, match in enumerate(matches, 1):
            entry = add(("document", match.document.id), rank, kind)
            entry.match = entry.match or match  # keep the snippet from the first retriever

    ranked = sorted(fused.values(), key=lambda e: e.score, reverse=True)[:limit]
    hits: list[SearchHit] = []
    for entry in ranked:
        score = round(entry.score, 6)
        if entry.client is not None:
            hits.append(
                ClientSearchHit(
                    score=score,
                    matched_by=entry.matched_by,
                    client=ClientOut.model_validate(entry.client),
                )
            )
        elif entry.match is not None:
            hits.append(
                DocumentSearchHit(
                    score=score,
                    matched_by=entry.matched_by,
                    document=DocumentBrief.model_validate(entry.match.document),
                    snippet=_snippet(entry.match.snippet),
                )
            )
    return hits
