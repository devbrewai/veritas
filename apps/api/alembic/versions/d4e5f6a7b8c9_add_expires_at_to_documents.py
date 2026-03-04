"""add expires_at to documents

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-03-04 12:00:00.000000

GDPR retention: documents expire after DOCUMENT_RETENTION_DAYS (default 30).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add expires_at column for document retention."""
    op.add_column(
        "documents",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    # Backfill existing rows: uploaded_at + 30 days
    op.execute(
        """
        UPDATE documents
        SET expires_at = uploaded_at + interval '30 days'
        WHERE expires_at IS NULL
        """
    )
    op.create_index(
        op.f("ix_documents_expires_at"),
        "documents",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove expires_at column."""
    op.drop_index(op.f("ix_documents_expires_at"), table_name="documents")
    op.drop_column("documents", "expires_at")
