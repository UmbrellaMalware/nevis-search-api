"""Drop indexes covered by unique indexes, and the unused summary_attempts column.

ix_documents_client_id is covered by uq_documents_client_content_hash (client_id, content_hash),
ix_document_search_chunks_document_id by uq_document_search_chunks_position
(document_id, chunk_index): Postgres uses the leading column of those for the same lookups.
summary_attempts is unused: summaries are tried once (failed on error).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_documents_client_id", table_name="documents")
    op.drop_index("ix_document_search_chunks_document_id", table_name="document_search_chunks")
    op.drop_column("documents", "summary_attempts")


def downgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("summary_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_document_search_chunks_document_id", "document_search_chunks", ["document_id"]
    )
    op.create_index("ix_documents_client_id", "documents", ["client_id"])
