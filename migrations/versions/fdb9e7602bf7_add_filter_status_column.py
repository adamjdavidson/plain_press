"""add_filter_status_column

Revision ID: fdb9e7602bf7
Revises: d9f1e2a3b4c5
Create Date: 2025-11-29 15:55:39.178854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fdb9e7602bf7'
down_revision: Union[str, Sequence[str], None] = 'd9f1e2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add filter_status column for background worker processing."""
    # Create the enum type
    filter_status_enum = postgresql.ENUM(
        'unfiltered', 'filtering', 'passed', 'rejected',
        name='filter_status'
    )
    filter_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Add column with default value
    op.add_column(
        'articles',
        sa.Column(
            'filter_status',
            sa.Enum('unfiltered', 'filtering', 'passed', 'rejected', name='filter_status'),
            nullable=False,
            server_default='unfiltered'
        )
    )
    
    # Create index for efficient worker polling
    op.create_index('ix_articles_filter_status', 'articles', ['filter_status'], unique=False)


def downgrade() -> None:
    """Remove filter_status column."""
    op.drop_index('ix_articles_filter_status', table_name='articles')
    op.drop_column('articles', 'filter_status')
    
    # Drop the enum type
    filter_status_enum = postgresql.ENUM(
        'unfiltered', 'filtering', 'passed', 'rejected',
        name='filter_status'
    )
    filter_status_enum.drop(op.get_bind(), checkfirst=True)
