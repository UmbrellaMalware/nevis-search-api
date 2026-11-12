"""Hybrid search across clients and documents.

Four independent retrievers each produce a ranked list:

* clients   / lexical   - substring + trigram match on email, full name, description
* clients   / semantic  - Sentence-BERT similarity of the client description
* documents / semantic  - Sentence-BERT similarity of the best chunk
* documents / full-text - Postgres full-text match on chunks

The query is first expanded with domain synonyms from the `search_synonyms` table (e.g.
"address proof" -> "utility bill", ...); semantic retrievers take the best similarity over the
query and its synonyms, full-text ORs the synonym phrases in.

The lists are merged with Reciprocal Rank Fusion (see `app.services.fusion`), so trigram
similarity, cosine similarity and ts_rank never have to be compared directly, and an item found
by several retrievers naturally rises to the top.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client
from app.repositories.clients import ClientRepository
from app.repositories.documents import DocumentMatch, DocumentRepository
from app.repositories.synonyms import SynonymRepository
from app.services.dto import (
    ClientDTO,
    ClientHit,
    DocumentBriefDTO,
    DocumentHit,
    MatchType,
    SearchResult,
)
from app.services.embeddings import Embedder
from app.services.fusion import Fused, reciprocal_rank_fusion

SNIPPET_CHARS = 300
MIN_LEXICAL_QUERY_CHARS = 2  # a single character would substring-match nearly everything

type _Candidate = Client | DocumentMatch
type _RankedList = tuple[MatchType, Sequence[_Candidate]]


async def search(
    session: AsyncSession,
    embedder: Embedder,
    query: str,
    *,
    min_similarity: float,
    limit: int,
) -> list[SearchResult]:
    """Search clients and documents; return one list, best match first (at most `limit`)."""
    query = query.strip()
    synonyms, vectors = await _expand_and_embed(session, embedder, query)

    ranked_lists: list[_RankedList] = [
        *await _rank_clients(session, query, vectors, min_similarity=min_similarity, limit=limit),
        *await _rank_documents(
            session, query, synonyms, vectors, min_similarity=min_similarity, limit=limit
        ),
    ]
    fused = reciprocal_rank_fusion(ranked_lists, key=_identity)
    return [_to_result(entry) for entry in fused[:limit]]


async def _expand_and_embed(
    session: AsyncSession, embedder: Embedder, query: str
) -> tuple[list[str], list[list[float]]]:
    """Find glossary synonyms of the query and embed the query together with them.

    "address proof"       -> (["utility bill", "bank statement", ...],
                              [vector("address proof"), vector("utility bill"), ...])
    "investment strategy" -> ([], [vector("investment strategy")])
    """
    synonyms = await SynonymRepository(session).expand(query)
    vectors = await embedder.embed([query, *synonyms])
    return synonyms, vectors


async def _rank_clients(
    session: AsyncSession,
    query: str,
    vectors: list[list[float]],
    *,
    min_similarity: float,
    limit: int,
) -> list[tuple[MatchType, list[Client]]]:
    """Run the client retrievers; return each one's clients, best match first.

    Lexical (email, name, description; substring + typos) is skipped for one-character queries,
    which would substring-match almost every client.
    """
    clients = ClientRepository(session)
    ranked: list[tuple[MatchType, list[Client]]] = []
    if len(query) >= MIN_LEXICAL_QUERY_CHARS:
        lexical = await clients.search_lexical(query, limit)
        ranked.append((MatchType.LEXICAL, [client for client, _ in lexical]))
    semantic = await clients.search_semantic(vectors, min_similarity, limit)
    ranked.append((MatchType.SEMANTIC, [client for client, _ in semantic]))
    return ranked


async def _rank_documents(
    session: AsyncSession,
    query: str,
    synonyms: list[str],
    vectors: list[list[float]],
    *,
    min_similarity: float,
    limit: int,
) -> list[tuple[MatchType, list[DocumentMatch]]]:
    """Run the document retrievers; return each one's matches, best match first.

    Semantic comes first, so when both find a document, fusion keeps its snippet: the chunk
    closest in meaning rather than the one that merely shares words.
    """
    documents = DocumentRepository(session)
    semantic = await documents.search_semantic(vectors, min_similarity, limit)
    full_text = await documents.search_full_text(query, synonyms, limit)
    return [(MatchType.SEMANTIC, semantic), (MatchType.FULL_TEXT, full_text)]


def _identity(candidate: _Candidate) -> tuple[str, uuid.UUID]:
    """What makes two retriever results the same item: a client and a document never collide."""
    if isinstance(candidate, Client):
        return "client", candidate.id
    return "document", candidate.document.id


def _to_result(entry: Fused[_Candidate, MatchType]) -> SearchResult:
    """Turn a fused retriever result into a client hit or a document hit."""
    if isinstance(entry.item, Client):
        return ClientHit(
            client=ClientDTO.model_validate(entry.item),
            score=entry.score,
            matched_by=list(entry.sources),
        )
    return DocumentHit(
        document=DocumentBriefDTO.model_validate(entry.item.document),
        snippet=_snippet(entry.item.snippet),
        score=entry.score,
        matched_by=list(entry.sources),
    )


def _snippet(text: str) -> str:
    """Shorten a matched chunk to at most SNIPPET_CHARS characters for the result list.

    A chunk is up to 150 words (~1000 characters): too long to show in a result list.

    "Electricity bill for March"  -> "Electricity bill for March"  (fits: unchanged)
    <a 1000-character chunk>      -> <its first 299 characters, trailing whitespace stripped>
                                     + "…"  (so the result is at most 300 characters)
    """
    if len(text) <= SNIPPET_CHARS:
        return text
    return text[: SNIPPET_CHARS - 1].rstrip() + "…"
