"""Documents: content hash, unique per client, to reject re-uploads of the same document.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("content_hash", sa.LargeBinary(), nullable=True))
    # Same value the app computes: hashlib.sha256(content.encode("utf-8")).digest().
    op.execute("UPDATE documents SET content_hash = sha256(convert_to(content, 'UTF8'))")
    op.alter_column("documents", "content_hash", nullable=False)
    op.create_index(
        "uq_documents_client_content_hash",
        "documents",
        ["client_id", "content_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_documents_client_content_hash", table_name="documents")
    op.drop_column("documents", "content_hash")
