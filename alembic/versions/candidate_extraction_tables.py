"""candidate extraction tables

Revision ID: candidate_extraction
Revises: 4d54b94d83ad
Create Date: 2026-08-11

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'candidate_extraction'
down_revision: str = '4d54b94d83ad'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # candidates table - normalized candidate pages from research
    op.create_table('candidates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('search_id', sa.Integer(), nullable=False, index=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False, index=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('kind', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('candidate_metadata', sa.JSON(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['search_id'], ['search_history.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidates_search_id'), 'candidates', ['search_id'], unique=False)
    op.create_index(op.f('ix_candidates_domain'), 'candidates', ['domain'], unique=False)
    op.create_index(op.f('ix_candidates_url'), 'candidates', ['url'], unique=False)

    # candidate_images table - images found on candidate pages
    op.create_table('candidate_images',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False, index=True),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('local_path', sa.String(length=512), nullable=True),
        sa.Column('sha256', sa.String(length=64), nullable=True, index=True),
        sa.Column('a_hash', sa.String(length=16), nullable=True),
        sa.Column('d_hash', sa.String(length=16), nullable=True),
        sa.Column('p_hash', sa.String(length=16), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('correlation_classification', sa.String(length=50), nullable=True),
        sa.Column('correlation_hamming_distance', sa.Integer(), nullable=True),
        sa.Column('face_similarity', sa.Float(), nullable=True),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_images_candidate_id'), 'candidate_images', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_candidate_images_sha256'), 'candidate_images', ['sha256'], unique=False)

    # candidate_profiles table - public profile links found
    op.create_table('candidate_profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False, index=True),
        sa.Column('profile_url', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(length=100), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True, index=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_profiles_candidate_id'), 'candidate_profiles', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_candidate_profiles_username'), 'candidate_profiles', ['username'], unique=False)

    # candidate_locations table - locations extracted from candidate pages
    op.create_table('candidate_locations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False, index=True),
        sa.Column('location', sa.String(length=512), nullable=False),
        sa.Column('location_type', sa.String(length=50), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_locations_candidate_id'), 'candidate_locations', ['candidate_id'], unique=False)

    # candidate_dates table - dates/timestamps extracted from candidate pages
    op.create_table('candidate_dates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False, index=True),
        sa.Column('date_value', sa.DateTime(timezone=True), nullable=False),
        sa.Column('date_type', sa.String(length=50), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidate_dates_candidate_id'), 'candidate_dates', ['candidate_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_candidate_dates_candidate_id'), table_name='candidate_dates')
    op.drop_table('candidate_dates')
    op.drop_index(op.f('ix_candidate_locations_candidate_id'), table_name='candidate_locations')
    op.drop_table('candidate_locations')
    op.drop_index(op.f('ix_candidate_profiles_username'), table_name='candidate_profiles')
    op.drop_index(op.f('ix_candidate_profiles_candidate_id'), table_name='candidate_profiles')
    op.drop_table('candidate_profiles')
    op.drop_index(op.f('ix_candidate_images_sha256'), table_name='candidate_images')
    op.drop_index(op.f('ix_candidate_images_candidate_id'), table_name='candidate_images')
    op.drop_table('candidate_images')
    op.drop_index(op.f('ix_candidates_url'), table_name='candidates')
    op.drop_index(op.f('ix_candidates_domain'), table_name='candidates')
    op.drop_index(op.f('ix_candidates_search_id'), table_name='candidates')
    op.drop_table('candidates')