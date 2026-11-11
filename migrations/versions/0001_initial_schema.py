"""Initial schema: clients, documents, document chunks with embeddings.

Revision ID: 0001
Revises:
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "social_links",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("description_embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("uq_clients_email_lower", "clients", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column(
            "client_id",
            sa.Uuid(),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "summary_status",
            sa.Enum("pending", "ready", "failed", name="summary_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("summary_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary_error", sa.Text(), nullable=True),
    )
    op.create_index("ix_documents_client_id", "documents", ["client_id"])
    # Small partial index: the summary worker only ever scans pending rows.
    op.create_index(
        "ix_documents_summary_pending",
        "documents",
        ["created_at"],
        postgresql_where=sa.text("summary_status = 'pending'"),
    )

    op.create_table(
        "document_search_chunks",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_search_chunks_position"
        ),
    )
    op.create_index(
        "ix_document_search_chunks_document_id", "document_search_chunks", ["document_id"]
    )
    op.execute(
        "CREATE INDEX ix_document_search_chunks_embedding ON document_search_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("document_search_chunks")
    op.drop_table("documents")
    op.drop_table("clients")
    op.execute("DROP TYPE IF EXISTS summary_status")
