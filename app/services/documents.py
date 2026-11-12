import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ClientNotFoundError
from app.models import Document, DocumentSearchChunk
from app.repositories.clients import ClientRepository
from app.repositories.documents import DocumentRepository
from app.services.chunking import chunk_text
from app.services.dto import DocumentCreateData, DocumentDTO
from app.services.embeddings import Embedder


async def create_document(
    session: AsyncSession,
    embedder: Embedder,
    client_id: uuid.UUID,
    data: DocumentCreateData,
) -> DocumentDTO:
    """Create a document and its search chunks. Raises ClientNotFoundError for unknown clients."""
    if not await ClientRepository(session).exists(client_id):
        raise ClientNotFoundError(client_id)

    # Embeddings are computed synchronously so the document is searchable as soon as
    # the request returns. The title is prepended so every chunk carries its context.
    pieces = chunk_text(data.content)
    vectors = await embedder.embed([f"{data.title}\n{piece}" for piece in pieces])

    document = await DocumentRepository(session).add(
        Document(
            client_id=client_id,
            title=data.title,
            content=data.content,
            search_chunks=[
                DocumentSearchChunk(chunk_index=i, content=piece, embedding=vector)
                for i, (piece, vector) in enumerate(zip(pieces, vectors, strict=True))
            ],
        )
    )
    await session.commit()
    return DocumentDTO.model_validate(document)
