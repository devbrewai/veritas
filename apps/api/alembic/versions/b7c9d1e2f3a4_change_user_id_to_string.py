"""change_user_id_to_string

Revision ID: b7c9d1e2f3a4
Revises: 49f317125177
Create Date: 2026-02-03 14:30:00.000000

This migration changes user_id columns from UUID to String(255) to support
Better Auth's nanoid-style string IDs instead of UUIDs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c9d1e2f3a4'
down_revision: Union[str, Sequence[str], None] = '49f317125177'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change user_id columns from UUID to String(255) for Better Auth compatibility."""
    # For PostgreSQL, we need to alter the column type
    # First drop the existing indexes
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    op.drop_index(op.f('ix_screening_results_user_id'), table_name='screening_results')

    # Delete existing data since UUID format won't convert to nanoid strings
    # In production, you would migrate data by mapping UUIDs to Better Auth user IDs
    op.execute("DELETE FROM screening_results")
    op.execute("DELETE FROM documents")

    # Alter columns from UUID to String(255)
    # For PostgreSQL, we need to use raw SQL for the type change
    op.execute("ALTER TABLE documents ALTER COLUMN user_id TYPE VARCHAR(255)")
    op.execute("ALTER TABLE screening_results ALTER COLUMN user_id TYPE VARCHAR(255)")

    # Recreate indexes
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
    op.create_index(op.f('ix_screening_results_user_id'), 'screening_results', ['user_id'], unique=False)


def downgrade() -> None:
    """Change user_id columns back from String to UUID."""
    # Drop indexes
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    op.drop_index(op.f('ix_screening_results_user_id'), table_name='screening_results')

    # Delete data since string format won't convert to UUID
    op.execute("DELETE FROM screening_results")
    op.execute("DELETE FROM documents")

    # Alter columns from String back to UUID
    op.execute("ALTER TABLE documents ALTER COLUMN user_id TYPE UUID USING user_id::uuid")
    op.execute("ALTER TABLE screening_results ALTER COLUMN user_id TYPE UUID USING user_id::uuid")

    # Recreate indexes
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
    op.create_index(op.f('ix_screening_results_user_id'), 'screening_results', ['user_id'], unique=False)
