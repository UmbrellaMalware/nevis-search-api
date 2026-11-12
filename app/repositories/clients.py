import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Text, case, exists, func, literal, literal_column, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import QueryableAttribute

from app.exceptions import EmailAlreadyExistsError
from app.models import Client
from app.repositories.best_scores import BestScores

EMAIL_UNIQUE_INDEX = "uq_clients_email_lower"

# Same expression as the ix_clients_full_name_trgm index, so the planner can use it.
_FULL_NAME: ColumnElement[str] = Client.first_name.op("||")(literal_column("' '")).op("||")(
    Client.last_name
)

# Fields searched by search_lexical; each one has a trigram GIN index (migration 0002).
_LEXICAL_FIELDS: tuple[ColumnElement[Any] | QueryableAttribute[Any], ...] = (
    Client.email,
    _FULL_NAME,
    Client.description,
)


class ClientRepository:
    """Data access for clients. Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, client_id: uuid.UUID) -> bool:
        return bool(await self._session.scalar(select(exists().where(Client.id == client_id))))

    async def add(self, client: Client) -> Client:
        """Insert a client. Raises EmailAlreadyExistsError if the email is taken (any case).

        Duplicates are detected by the unique index on lower(email), not by checking first:
        with "SELECT exists, then INSERT" two concurrent requests can both see "free" and both
        insert. The index is the only check the database enforces atomically, and it costs no
        extra query.
        """
        self._session.add(client)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            if _violated_constraint(exc) == EMAIL_UNIQUE_INDEX:
                raise EmailAlreadyExistsError(client.email) from exc
            raise
        return client

    async def search_lexical(self, query: str, limit: int) -> list[tuple[Client, float]]:
        """Clients whose email, full name or description contains the query or a near-spelling.

        "NevisWealth" -> john.doe@neviswealth.com, score 1.0    (substring, any case)
        "neviswelth"  -> john.doe@neviswealth.com, score < 1.0   (typo: fuzzy match)
        Substring hits score 1.0, fuzzy hits their word similarity; best first.
        """
        q = literal(query, Text)
        contains = _contains(query)
        score = case((contains, 1.0), else_=_best_word_similarity(q))

        rows = await self._session.execute(
            select(Client, score)
            .where(or_(contains, _similar_word(q)))
            .order_by(score.desc(), Client.created_at)
            .limit(limit)
        )
        return [(client, float(s)) for client, s in rows]

    async def search_semantic(
        self, vectors: Sequence[list[float]], min_similarity: float, limit: int
    ) -> list[tuple[Client, float]]:
        """Clients whose description is semantically close to any of the query vectors."""
        best: BestScores[uuid.UUID, Client] = BestScores()
        for vector in vectors:
            distance = Client.description_embedding.cosine_distance(vector)
            rows = await self._session.execute(
                select(Client, distance)
                .where(Client.description_embedding.is_not(None))
                .where(distance <= 1 - min_similarity)
                .order_by(distance)
                .limit(limit)
            )
            for client, dist in rows:
                best.offer(client.id, client, 1 - float(dist))
        return [(client, similarity) for _, client, similarity in best.top(limit)]


def _violated_constraint(exc: IntegrityError) -> str | None:
    # SQLAlchemy wraps the driver error; asyncpg exposes the constraint/index name on the cause.
    driver_error = exc.orig.__cause__ if exc.orig is not None else None
    name = getattr(driver_error, "constraint_name", None)
    return name if isinstance(name, str) else None


def _escape_like(value: str) -> str:
    """Make LIKE wildcards literal: "100%_sure" -> "100\%\_sure"."""
    return value.replace("\\", "\\\\").replace("%", "\%").replace("_", "\_")


def _contains(query: str) -> ColumnElement[bool]:
    """Some field contains the query, ignoring case (ILIKE '%query%').

    "NevisWealth" matches the email "john.doe@neviswealth.com".
    "%" and "_" in the query are matched literally, not as wildcards.
    """
    pattern = f"%{_escape_like(query)}%"
    return or_(*(field.ilike(pattern, escape="\\") for field in _LEXICAL_FIELDS))


def _similar_word(q: ColumnElement[str]) -> ColumnElement[bool]:
    """Some field has a word spelled close to the query: catches typos.

    `query <% field` is pg_trgm's word-similarity operator: true when
    word_similarity(query, field) >= pg_trgm.word_similarity_threshold (0.6 by default), i.e.
    the query's trigrams mostly occur in some stretch of the field. Served by the trigram indexes.

    "neviswelth" matches "john.doe@neviswealth.com"; "smith" does not match "john.doe@...".
    """
    return or_(*(q.op("<%")(field) for field in _LEXICAL_FIELDS))


def _best_word_similarity(q: ColumnElement[str]) -> ColumnElement[float]:
    """The highest word_similarity(query, field) over the fields, from 0 to 1.

    A missing description (NULL) counts as 0 instead of making the whole result NULL.
    """
    return func.greatest(
        *(func.coalesce(func.word_similarity(q, field), 0.0) for field in _LEXICAL_FIELDS)
    )
