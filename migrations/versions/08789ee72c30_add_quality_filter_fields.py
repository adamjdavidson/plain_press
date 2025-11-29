"""add_quality_filter_fields

Revision ID: 08789ee72c30
Revises: c8f2a3b4d5e6
Create Date: 2025-11-29 11:35:40.521900

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08789ee72c30'
down_revision: Union[str, Sequence[str], None] = 'c8f2a3b4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add content_type and wow_score columns to articles table."""
    op.add_column('articles', sa.Column('content_type', sa.String(50), nullable=True))
    op.add_column('articles', sa.Column('wow_score', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove content_type and wow_score columns from articles table."""
    op.drop_column('articles', 'wow_score')
    op.drop_column('articles', 'content_type')
