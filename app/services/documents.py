import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ClientNotFoundError, DocumentAlreadyExistsError
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
    """Create a document and its search chunks.

    Raises ClientNotFoundError for unknown clients and DocumentAlreadyExistsError if the client
    already has a document with the same content (the title does not matter).
    """
    if not await ClientRepository(session).exists(client_id):
        raise ClientNotFoundError(client_id)

    documents = DocumentRepository(session)
    content_hash = _content_hash(data.content)
    # Checked before embedding, so a re-upload fails fast instead of embedding 100k characters.
    # The unique index in DocumentRepository.add still catches concurrent uploads.
    if existing := await documents.find_id_by_content_hash(client_id, content_hash):
        raise DocumentAlreadyExistsError(client_id, existing)

    # Embeddings are computed synchronously so the document is searchable as soon as
    # the request returns. The title is prepended so every chunk carries its context.
    pieces = chunk_text(data.content)
    vectors = await embedder.embed([f"{data.title}\n{piece}" for piece in pieces])

    document = await documents.add(
        Document(
            client_id=client_id,
            title=data.title,
            content=data.content,
            content_hash=content_hash,
            search_chunks=[
                DocumentSearchChunk(chunk_index=i, content=piece, embedding=vector)
                for i, (piece, vector) in enumerate(zip(pieces, vectors, strict=True))
            ],
        )
    )
    await session.commit()
    return DocumentDTO.model_validate(document)


def _content_hash(content: str) -> bytes:
    """SHA-256 of the content's UTF-8 bytes: equal for byte-identical content only.

    "Electricity bill for March" -> b"\\x9f\\x1c..."  (32 bytes)
    Migration 0003 computes the same value in SQL: sha256(convert_to(content, 'UTF8')).
    """
    return hashlib.sha256(content.encode("utf-8")).digest()
