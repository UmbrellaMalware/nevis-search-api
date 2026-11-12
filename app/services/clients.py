from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client
from app.repositories.clients import ClientRepository
from app.services.dto import ClientCreateData, ClientDTO
from app.services.embeddings import Embedder


async def create_client(
    session: AsyncSession, embedder: Embedder, data: ClientCreateData
) -> ClientDTO:
    """Create a client. Raises EmailAlreadyExistsError if the email is taken (any case)."""
    embedding = (await embedder.embed([data.description]))[0] if data.description else None

    client = await ClientRepository(session).add(
        Client(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            description=data.description,
            social_links=data.social_links,
            description_embedding=embedding,
        )
    )
    await session.commit()
    return ClientDTO.model_validate(client)
