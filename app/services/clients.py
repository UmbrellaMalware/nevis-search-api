from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client
from app.repositories.clients import ClientRepository
from app.services.dto import ClientCreateData, ClientDTO
from app.services.embeddings import Embedder


async def create_client(
    session: AsyncSession, embedder: Embedder, data: ClientCreateData
) -> ClientDTO:
    """Create a client. Raises EmailAlreadyExistsError if the email is taken (any case)."""
    client = await ClientRepository(session).add(
        Client(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            description=data.description,
            social_links=data.social_links,
            description_embedding=await _embed_description(embedder, data.description),
        )
    )
    await session.commit()
    return ClientDTO.model_validate(client)


async def _embed_description(embedder: Embedder, description: str | None) -> list[float] | None:
    """Vector for semantic search over the client's description.

    "Wealth manager focused on retirement planning" -> [0.03, ...]  (EMBEDDING_DIM numbers)
    None (no description)                           -> None (nothing to search by meaning;
                                                       semantic client search skips the client)
    """
    if not description:
        return None
    return await embedder.embed_one(description)
