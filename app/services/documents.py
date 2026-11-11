import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ClientNotFoundError
from app.models import Client, Document, DocumentSearchChunk
from app.schemas import DocumentCreate
from app.services.chunking import chunk_text
from app.services.embeddings import Embedder


async def create_document(
    session: AsyncSession,
    embedder: Embedder,
    client_id: uuid.UUID,
    data: DocumentCreate,
) -> Document:
    if await session.scalar(select(Client.id).where(Client.id == client_id)) is None:
        raise ClientNotFoundError(client_id)

    # Embeddings are computed synchronously so the document is searchable as soon as
    # the request returns. The title is prepended so every chunk carries its context.
    pieces = chunk_text(data.content)
    vectors = await embedder.embed([f"{data.title}\n{piece}" for piece in pieces])

    document = Document(
        client_id=client_id,
        title=data.title,
        content=data.content,
        search_chunks=[
            DocumentSearchChunk(chunk_index=i, content=piece, embedding=vector)
            for i, (piece, vector) in enumerate(zip(pieces, vectors, strict=True))
        ],
    )
    session.add(document)
    await session.commit()
    return document
