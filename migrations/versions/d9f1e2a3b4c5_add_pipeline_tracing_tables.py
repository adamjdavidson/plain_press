"""Add pipeline tracing tables

Revision ID: d9f1e2a3b4c5
Revises: 08789ee72c30
Create Date: 2025-11-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd9f1e2a3b4c5'
down_revision: Union[str, None] = '08789ee72c30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pipeline_run_status enum
    pipeline_run_status = postgresql.ENUM(
        'running', 'completed', 'failed',
        name='pipeline_run_status'
    )
    pipeline_run_status.create(op.get_bind(), checkfirst=True)
    
    # Create pipeline_runs table
    op.create_table(
        'pipeline_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', postgresql.ENUM('running', 'completed', 'failed', name='pipeline_run_status', create_type=False), nullable=False),
        sa.Column('input_count', sa.Integer(), nullable=False, default=0),
        sa.Column('filter1_pass_count', sa.Integer(), nullable=True),
        sa.Column('filter2_pass_count', sa.Integer(), nullable=True),
        sa.Column('filter3_pass_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pipeline_runs_started_at', 'pipeline_runs', ['started_at'], unique=False)
    op.create_index('ix_pipeline_runs_status', 'pipeline_runs', ['status'], unique=False)
    
    # Create filter_traces table
    op.create_table(
        'filter_traces',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_url', sa.String(500), nullable=False),
        sa.Column('article_title', sa.String(500), nullable=False),
        sa.Column('filter_name', sa.String(50), nullable=False),
        sa.Column('filter_order', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['pipeline_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_filter_traces_run_id', 'filter_traces', ['run_id'], unique=False)
    op.create_index('ix_filter_traces_filter_name', 'filter_traces', ['filter_name'], unique=False)
    op.create_index('ix_filter_traces_decision', 'filter_traces', ['decision'], unique=False)
    op.create_index('ix_filter_traces_created_at', 'filter_traces', ['created_at'], unique=False)
    
    # Add last_run_id column to articles table
    op.add_column('articles', sa.Column('last_run_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_articles_last_run_id',
        'articles', 'pipeline_runs',
        ['last_run_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop last_run_id from articles
    op.drop_constraint('fk_articles_last_run_id', 'articles', type_='foreignkey')
    op.drop_column('articles', 'last_run_id')
    
    # Drop filter_traces table
    op.drop_index('ix_filter_traces_created_at', table_name='filter_traces')
    op.drop_index('ix_filter_traces_decision', table_name='filter_traces')
    op.drop_index('ix_filter_traces_filter_name', table_name='filter_traces')
    op.drop_index('ix_filter_traces_run_id', table_name='filter_traces')
    op.drop_table('filter_traces')
    
    # Drop pipeline_runs table
    op.drop_index('ix_pipeline_runs_status', table_name='pipeline_runs')
    op.drop_index('ix_pipeline_runs_started_at', table_name='pipeline_runs')
    op.drop_table('pipeline_runs')
    
    # Drop enum
    pipeline_run_status = postgresql.ENUM('running', 'completed', 'failed', name='pipeline_run_status')
    pipeline_run_status.drop(op.get_bind(), checkfirst=True)

