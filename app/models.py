import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    LargeBinary,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Output dimension of the embedding model (all-MiniLM-L6-v2 and its fine-tune): the length of
# every vector stored in the database.
EMBEDDING_DIM = 384


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SummaryStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    first_name: Mapped[str]
    last_name: Mapped[str]
    # Uniqueness is enforced case-insensitively by a unique index on lower(email).
    email: Mapped[str]
    description: Mapped[str | None]
    social_links: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    description_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), deferred=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    documents: Mapped[list[Document]] = relationship(
        back_populates="client", cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str]
    content: Mapped[str]
    # SHA-256 of the UTF-8 content; unique per client (uq_documents_client_content_hash).
    content_hash: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    # Summary is produced asynchronously by the worker; these columns double as its job queue.
    summary: Mapped[str | None]
    summary_status: Mapped[SummaryStatus] = mapped_column(
        Enum(
            SummaryStatus,
            name="summary_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=SummaryStatus.PENDING,
    )
    summary_attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    summary_error: Mapped[str | None]

    client: Mapped[Client] = relationship(back_populates="documents", lazy="raise")
    search_chunks: Mapped[list[DocumentSearchChunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
        order_by="DocumentSearchChunk.chunk_index",
    )


class DocumentSearchChunk(Base):
    """A slice of a document's content with its embedding: the unit of document search.

    Derived data: it can always be rebuilt from `documents.content` (e.g. after a model change).
    """

    __tablename__ = "document_search_chunks"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int]
    content: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    # Full-text index of the chunk, maintained by Postgres (generated column).
    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', content)", persisted=True), deferred=True
    )

    document: Mapped[Document] = relationship(back_populates="search_chunks", lazy="raise")


class SearchSynonym(Base):
    """Domain glossary for query expansion: a query containing `term` also searches `synonym`.

    Terms and synonyms are stored lowercase, words separated by single spaces.
    """

    __tablename__ = "search_synonyms"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    term: Mapped[str]
    synonym: Mapped[str]
