from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


class DocumentRepository:
    """Data access for documents. Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> Document:
        """Persist a document together with its search chunks (cascaded by the relationship)."""
        self._session.add(document)
        await self._session.flush()
        return document
