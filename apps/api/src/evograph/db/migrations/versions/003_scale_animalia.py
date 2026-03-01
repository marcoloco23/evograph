"""Add pipeline_runs table and species-only partial index.

Revision ID: 003
Revises: 002
Create Date: 2026-03-01

Supports Phase 2 scaling:
- pipeline_runs table for tracking background pipeline jobs
- Partial index on taxa where rank='species' for faster species queries
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pipeline runs table
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("progress", JSONB, nullable=True),
        sa.Column("celery_task_id", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_pipeline_runs_step", "pipeline_runs", ["step"])
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])

    # Partial index on taxa for species-only queries (used by NCBI ingestion)
    op.execute(
        "CREATE INDEX ix_taxa_species_only ON taxa (ott_id) WHERE rank = 'species'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_taxa_species_only")
    op.drop_index("ix_pipeline_runs_status")
    op.drop_index("ix_pipeline_runs_step")
    op.drop_table("pipeline_runs")
