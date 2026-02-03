"""add_user_id_to_documents_and_screening

Revision ID: 49f317125177
Revises: fd8fec1f9824
Create Date: 2026-02-03 10:06:51.635344

This migration adds user_id columns for multi-tenant isolation.
Better Auth tables (user, account, session, verification, jwks) are
managed separately and should NOT be touched by Alembic.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49f317125177'
down_revision: Union[str, Sequence[str], None] = 'fd8fec1f9824'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id columns to documents and screening_results tables."""
    # Delete existing data since we can't assign user_id to orphaned records
    # In production, you would migrate data by assigning a default user
    op.execute("DELETE FROM screening_results")
    op.execute("DELETE FROM documents")

    # Add user_id column to documents
    op.add_column('documents', sa.Column('user_id', sa.Uuid(), nullable=False))
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)

    # Add user_id column to screening_results
    op.add_column('screening_results', sa.Column('user_id', sa.Uuid(), nullable=False))
    op.create_index(op.f('ix_screening_results_user_id'), 'screening_results', ['user_id'], unique=False)


def downgrade() -> None:
    """Remove user_id columns from documents and screening_results tables."""
    op.drop_index(op.f('ix_screening_results_user_id'), table_name='screening_results')
    op.drop_column('screening_results', 'user_id')
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    op.drop_column('documents', 'user_id')
