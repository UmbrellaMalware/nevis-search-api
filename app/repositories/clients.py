import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Text, case, exists, func, literal, literal_column, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import QueryableAttribute

from app.exceptions import EmailAlreadyExistsError
from app.models import Client

EMAIL_UNIQUE_INDEX = "uq_clients_email_lower"


def _violated_constraint(exc: IntegrityError) -> str | None:
    # SQLAlchemy wraps the driver error; asyncpg exposes the constraint/index name on the cause.
    driver_error = exc.orig.__cause__ if exc.orig is not None else None
    name = getattr(driver_error, "constraint_name", None)
    return name if isinstance(name, str) else None


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Same expression as the ix_clients_full_name_trgm index, so the planner can use it.
_FULL_NAME: ColumnElement[str] = Client.first_name.op("||")(literal_column("' '")).op("||")(
    Client.last_name
)


class ClientRepository:
    """Data access for clients. Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, client_id: uuid.UUID) -> bool:
        return bool(await self._session.scalar(select(exists().where(Client.id == client_id))))

    async def add(self, client: Client) -> Client:
        self._session.add(client)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            if _violated_constraint(exc) == EMAIL_UNIQUE_INDEX:
                raise EmailAlreadyExistsError(client.email) from exc
            raise
        return client

    async def search_lexical(self, query: str, limit: int) -> list[tuple[Client, float]]:
        """Case-insensitive substring or fuzzy (trigram word-similarity) match.

        Covers e.g. "NevisWealth" -> john.doe@neviswealth.com (substring) and typos such as
        "neviswelth" (word similarity above pg_trgm's 0.6 default threshold).
        Substring hits score 1.0; fuzzy hits score their word similarity.
        """
        q = literal(query, Text)
        pattern = f"%{_escape_like(query)}%"
        fields: list[ColumnElement[Any] | QueryableAttribute[Any]] = [
            Client.email,
            _FULL_NAME,
            Client.description,
        ]

        substring = or_(*(f.ilike(pattern, escape="\\") for f in fields))
        fuzzy = or_(*(q.op("<%")(f) for f in fields))
        similarity = func.greatest(
            *(func.coalesce(func.word_similarity(q, f), 0.0) for f in fields)
        )
        score = case((substring, 1.0), else_=similarity)

        rows = await self._session.execute(
            select(Client, score)
            .where(or_(substring, fuzzy))
            .order_by(score.desc(), Client.created_at)
            .limit(limit)
        )
        return [(client, float(s)) for client, s in rows]

    async def search_semantic(
        self, vectors: Sequence[list[float]], min_similarity: float, limit: int
    ) -> list[tuple[Client, float]]:
        """Clients whose description is semantically close to any of the query vectors."""
        best: dict[uuid.UUID, tuple[Client, float]] = {}
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
                similarity = 1 - float(dist)
                if client.id not in best or similarity > best[client.id][1]:
                    best[client.id] = (client, similarity)
        return sorted(best.values(), key=lambda pair: pair[1], reverse=True)[:limit]
