"""search results api tables

Revision ID: search_results_api
Revises: image_correlation
Create Date: 2026-08-11

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'search_results_api'
down_revision: str = 'image_correlation'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # searches table - main search records
    op.create_table('searches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True, index=True),
        sa.Column('image_id', sa.String(length=36), nullable=False, index=True),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
        sa.Column('uploaded_image', sa.String(length=512), nullable=False),
        sa.Column('providers', sa.JSON(), nullable=True),
        sa.Column('ranked_evidence', sa.JSON(), nullable=True),
        sa.Column('sources_checked', sa.Integer(), nullable=True, default=0),
        sa.Column('pages_analyzed', sa.Integer(), nullable=True, default=0),
        sa.Column('total_candidates', sa.Integer(), nullable=True, default=0),
        sa.Column('total_evidence', sa.Integer(), nullable=True, default=0),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_searches_user_id'), 'searches', ['user_id'], unique=False)
    op.create_index(op.f('ix_searches_image_id'), 'searches', ['image_id'], unique=False)
    op.create_index(op.f('ix_searches_status'), 'searches', ['status'], unique=False)
    op.create_index(op.f('ix_searches_created_at'), 'searches', ['started_at'], unique=False)

    # search_events table - SSE event stream for live progress
    op.create_table('search_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('search_id', sa.Integer(), nullable=False, index=True),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['search_id'], ['searches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_search_events_search_id'), 'search_events', ['search_id'], unique=False)
    op.create_index(op.f('ix_search_events_sequence'), 'search_events', ['sequence'], unique=False)
    op.create_index('ix_search_events_search_sequence', 'search_events', ['search_id', 'sequence'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_search_events_search_sequence', table_name='search_events')
    op.drop_index(op.f('ix_search_events_sequence'), table_name='search_events')
    op.drop_index(op.f('ix_search_events_search_id'), table_name='search_events')
    op.drop_table('search_events')
    op.drop_index(op.f('ix_searches_created_at'), table_name='searches')
    op.drop_index(op.f('ix_searches_status'), table_name='searches')
    op.drop_index(op.f('ix_searches_image_id'), table_name='searches')
    op.drop_index(op.f('ix_searches_user_id'), table_name='searches')
    op.drop_table('searches')