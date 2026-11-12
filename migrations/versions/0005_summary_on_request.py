"""Summaries on request: new documents start as not_requested instead of pending.

Existing documents keep their status (pending ones are still summarised).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A new enum value cannot be used in the transaction that adds it, so add it on its own.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE summary_status ADD VALUE IF NOT EXISTS 'not_requested'")
    op.execute("ALTER TABLE documents ALTER COLUMN summary_status SET DEFAULT 'not_requested'")


def downgrade() -> None:
    # Postgres cannot drop an enum value; treat "not requested" as requested instead.
    op.execute("ALTER TABLE documents ALTER COLUMN summary_status SET DEFAULT 'pending'")
    op.execute(
        "UPDATE documents SET summary_status = 'pending' WHERE summary_status = 'not_requested'"
    )
