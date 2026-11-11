from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client
from app.schemas import ClientCreate
from app.services.embeddings import Embedder


class EmailAlreadyExistsError(Exception):
    def __init__(self, email: str) -> None:
        super().__init__(f"A client with email '{email}' already exists")


async def create_client(session: AsyncSession, embedder: Embedder, data: ClientCreate) -> Client:
    embedding = (await embedder.embed([data.description]))[0] if data.description else None

    client = Client(
        first_name=data.first_name,
        last_name=data.last_name,
        email=str(data.email),
        description=data.description,
        social_links=data.social_links,
        description_embedding=embedding,
    )
    session.add(client)
    try:
        await session.commit()
    except IntegrityError as exc:
        # The only unique constraint on clients is lower(email).
        await session.rollback()
        raise EmailAlreadyExistsError(str(data.email)) from exc
    return client
