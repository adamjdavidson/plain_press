"""add_article_management_fields

Add is_published, is_rejected, topics fields to Article.
Add EmailSettings table for email customization.

Revision ID: c8f2a3b4d5e6
Revises: 07e13d1b6445
Create Date: 2025-11-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY


# revision identifiers, used by Alembic.
revision: str = 'c8f2a3b4d5e6'
down_revision: Union[str, Sequence[str], None] = '07e13d1b6445'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add article management fields and email settings table."""

    # Add new columns to articles table
    op.add_column('articles', sa.Column('is_published', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('articles', sa.Column('is_rejected', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('articles', sa.Column('topics', ARRAY(sa.String()), nullable=False, server_default='{}'))

    # Add indexes for the new columns
    op.create_index('ix_articles_is_published', 'articles', ['is_published'])
    op.create_index('ix_articles_is_rejected', 'articles', ['is_rejected'])

    # Create email_settings table
    op.create_table(
        'email_settings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('target_article_count', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('min_article_count', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('max_article_count', sa.Integer(), nullable=False, server_default='70'),
        sa.Column('max_per_source', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_per_topic', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('min_filter_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('recipient_email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Insert default email settings row
    op.execute("""
        INSERT INTO email_settings (target_article_count, min_article_count, max_article_count,
                                    max_per_source, max_per_topic, min_filter_score)
        VALUES (50, 30, 70, 5, 10, 0.5)
    """)


def downgrade() -> None:
    """Remove article management fields and email settings table."""

    # Drop email_settings table
    op.drop_table('email_settings')

    # Drop indexes
    op.drop_index('ix_articles_is_rejected', 'articles')
    op.drop_index('ix_articles_is_published', 'articles')

    # Drop columns from articles
    op.drop_column('articles', 'topics')
    op.drop_column('articles', 'is_rejected')
    op.drop_column('articles', 'is_published')
