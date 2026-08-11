"""evidence graph tables

Revision ID: evidence_graph
Revises: candidate_extraction
Create Date: 2026-08-11

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'evidence_graph'
down_revision: str = 'candidate_extraction'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # evidence_nodes table - nodes in the evidence graph
    op.create_table('evidence_nodes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('search_id', sa.Integer(), nullable=False, index=True),
        sa.Column('node_type', sa.String(length=50), nullable=False, index=True),
        sa.Column('entity_id', sa.String(length=255), nullable=False),
        sa.Column('entity_value', sa.Text(), nullable=False),
        sa.Column('attributes', sa.JSON(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('source_evidence_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['search_id'], ['search_history.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_nodes_search_id'), 'evidence_nodes', ['search_id'], unique=False)
    op.create_index(op.f('ix_evidence_nodes_node_type'), 'evidence_nodes', ['node_type'], unique=False)
    op.create_index(op.f('ix_evidence_nodes_entity_id'), 'evidence_nodes', ['entity_id'], unique=False)
    # Composite index for deduplication
    op.create_index('ix_evidence_nodes_search_type_entity', 'evidence_nodes', ['search_id', 'node_type', 'entity_id'], unique=False)

    # evidence_edges table - edges in the evidence graph
    op.create_table('evidence_edges',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('search_id', sa.Integer(), nullable=False, index=True),
        sa.Column('source_node_id', sa.Integer(), nullable=False, index=True),
        sa.Column('target_node_id', sa.Integer(), nullable=False, index=True),
        sa.Column('edge_type', sa.String(length=50), nullable=False, index=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('source_evidence_id', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('edge_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['search_id'], ['search_history.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_node_id'], ['evidence_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['evidence_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_edges_search_id'), 'evidence_edges', ['search_id'], unique=False)
    op.create_index(op.f('ix_evidence_edges_edge_type'), 'evidence_edges', ['edge_type'], unique=False)
    op.create_index(op.f('ix_evidence_edges_source_node_id'), 'evidence_edges', ['source_node_id'], unique=False)
    op.create_index(op.f('ix_evidence_edges_target_node_id'), 'evidence_edges', ['target_node_id'], unique=False)
    # Composite index for deduplication
    op.create_index('ix_evidence_edges_search_source_target_type', 'evidence_edges', ['search_id', 'source_node_id', 'target_node_id', 'edge_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_evidence_edges_search_source_target_type', table_name='evidence_edges')
    op.drop_index(op.f('ix_evidence_edges_target_node_id'), table_name='evidence_edges')
    op.drop_index(op.f('ix_evidence_edges_source_node_id'), table_name='evidence_edges')
    op.drop_index(op.f('ix_evidence_edges_edge_type'), table_name='evidence_edges')
    op.drop_index(op.f('ix_evidence_edges_search_id'), table_name='evidence_edges')
    op.drop_table('evidence_edges')
    op.drop_index('ix_evidence_nodes_search_type_entity', table_name='evidence_nodes')
    op.drop_index(op.f('ix_evidence_nodes_entity_id'), table_name='evidence_nodes')
    op.drop_index(op.f('ix_evidence_nodes_node_type'), table_name='evidence_nodes')
    op.drop_index(op.f('ix_evidence_nodes_search_id'), table_name='evidence_nodes')
    op.drop_table('evidence_nodes')