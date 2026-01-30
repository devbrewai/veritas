"""add screening_results table

Revision ID: a3f8b2c4d5e6
Revises: 2c52703be08a
Create Date: 2026-01-30 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f8b2c4d5e6"
down_revision: str | Sequence[str] | None = "2c52703be08a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create screening_results table."""
    op.create_table(
        "screening_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("customer_id", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=500), nullable=False),
        # Sanctions screening
        sa.Column(
            "sanctions_match",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "sanctions_decision",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'no_match'"),
        ),
        sa.Column("sanctions_score", sa.Float(), nullable=True),
        sa.Column("sanctions_details", sa.JSON(), nullable=True),
        # Adverse media (Day 4)
        sa.Column("adverse_media_count", sa.Integer(), nullable=True),
        sa.Column("adverse_media_summary", sa.JSON(), nullable=True),
        # Risk scoring (Day 4)
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("risk_tier", sa.String(length=20), nullable=True),
        sa.Column("risk_reasons", sa.JSON(), nullable=True),
        sa.Column("recommendation", sa.String(length=20), nullable=True),
        # Timestamps
        sa.Column(
            "screened_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name=op.f("pk_screening_results")),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_screening_results_document_id_documents"),
        ),
    )
    # Create indices
    op.create_index(
        op.f("ix_screening_results_document_id"),
        "screening_results",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_screening_results_customer_id"),
        "screening_results",
        ["customer_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop screening_results table."""
    op.drop_index(
        op.f("ix_screening_results_customer_id"),
        table_name="screening_results",
    )
    op.drop_index(
        op.f("ix_screening_results_document_id"),
        table_name="screening_results",
    )
    op.drop_table("screening_results")
