import uuid

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import EmailAlreadyExistsError
from app.models import Client

EMAIL_UNIQUE_INDEX = "uq_clients_email_lower"


def _violated_constraint(exc: IntegrityError) -> str | None:
    # SQLAlchemy wraps the driver error; asyncpg exposes the constraint/index name on the cause.
    driver_error = exc.orig.__cause__ if exc.orig is not None else None
    name = getattr(driver_error, "constraint_name", None)
    return name if isinstance(name, str) else None


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
