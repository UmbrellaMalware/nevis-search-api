"""Search: trigram + full-text + vector indexes, and the query-expansion glossary.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Initial KYC / wealth-management glossary. Extend it with plain INSERTs, no deploy needed.
SYNONYMS: dict[str, list[str]] = {
    "address proof": [
        "utility bill",
        "bank statement",
        "tenancy agreement",
        "council tax bill",
        "mortgage statement",
    ],
    "proof of address": [
        "utility bill",
        "bank statement",
        "tenancy agreement",
        "council tax bill",
        "mortgage statement",
    ],
    "proof of residence": ["utility bill", "tenancy agreement", "council tax bill"],
    "identity document": ["passport", "driving licence", "national identity card"],
    "proof of identity": ["passport", "driving licence", "national identity card"],
    "photo id": ["passport", "driving licence", "national identity card"],
    "source of funds": ["payslip", "bank statement", "sale agreement", "inheritance"],
    "source of wealth": ["payslip", "sale agreement", "inheritance", "tax return"],
    "proof of income": ["payslip", "employment contract", "tax return"],
}


def upgrade() -> None:
    # --- Clients: substring / fuzzy matching on email, full name and description ---
    op.execute("CREATE INDEX ix_clients_email_trgm ON clients USING gin (email gin_trgm_ops)")
    op.execute(
        "CREATE INDEX ix_clients_full_name_trgm ON clients "
        "USING gin ((first_name || ' ' || last_name) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_clients_description_trgm ON clients USING gin (description gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_clients_description_embedding ON clients "
        "USING hnsw (description_embedding vector_cosine_ops)"
    )

    # --- Document chunks: full-text search (exact terms that embeddings miss) ---
    op.add_column(
        "document_search_chunks",
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
            nullable=False,
        ),
    )
    op.execute(
        "CREATE INDEX ix_document_search_chunks_tsv ON document_search_chunks "
        "USING gin (search_tsv)"
    )

    # --- Query-expansion glossary ---
    synonyms = op.create_table(
        "search_synonyms",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("term", sa.Text(), nullable=False),
        sa.Column("synonym", sa.Text(), nullable=False),
        sa.UniqueConstraint("term", "synonym", name="uq_search_synonyms_pair"),
        sa.CheckConstraint(
            "term = lower(term) AND synonym = lower(synonym)", name="ck_search_synonyms_lower"
        ),
    )
    op.bulk_insert(
        synonyms,
        [{"term": t, "synonym": s} for t, syns in SYNONYMS.items() for s in syns],
    )


def downgrade() -> None:
    op.drop_table("search_synonyms")
    op.execute("DROP INDEX IF EXISTS ix_document_search_chunks_tsv")
    op.drop_column("document_search_chunks", "search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_clients_description_embedding")
    op.execute("DROP INDEX IF EXISTS ix_clients_description_trgm")
    op.execute("DROP INDEX IF EXISTS ix_clients_full_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_clients_email_trgm")
