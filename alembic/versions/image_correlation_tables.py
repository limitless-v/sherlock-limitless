"""image correlation tables

Revision ID: image_correlation
Revises: evidence_graph
Create Date: 2026-08-11

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'image_correlation'
down_revision: str = 'evidence_graph'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add correlation fields to candidate_extracted_images table
    op.add_column('candidate_extracted_images',
        sa.Column('correlation_classification', sa.String(length=50), nullable=True))
    op.add_column('candidate_extracted_images',
        sa.Column('correlation_hamming_distance', sa.Integer(), nullable=True))
    op.add_column('candidate_extracted_images',
        sa.Column('face_similarity', sa.Float(), nullable=True))
    op.add_column('candidate_extracted_images',
        sa.Column('correlation_confidence', sa.Float(), nullable=True))
    op.add_column('candidate_extracted_images',
        sa.Column('correlated_at', sa.DateTime(timezone=True), nullable=True))
    
    op.create_index(op.f('ix_candidate_extracted_images_correlation_classification'), 
                    'candidate_extracted_images', ['correlation_classification'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_candidate_extracted_images_correlation_classification'), 
                  table_name='candidate_extracted_images')
    op.drop_column('candidate_extracted_images', 'correlated_at')
    op.drop_column('candidate_extracted_images', 'correlation_confidence')
    op.drop_column('candidate_extracted_images', 'face_similarity')
    op.drop_column('candidate_extracted_images', 'correlation_hamming_distance')
    op.drop_column('candidate_extracted_images', 'correlation_classification')