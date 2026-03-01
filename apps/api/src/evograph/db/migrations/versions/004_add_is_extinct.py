"""Add is_extinct column to taxa table.

Revision ID: 004
Revises: 003
Create Date: 2026-03-01

Tracks extinction status from OpenTree taxonomy flags.
"""

from alembic import op
import sqlalchemy as sa


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "taxa",
        sa.Column("is_extinct", sa.Boolean(), nullable=True, server_default=None),
    )
    op.create_index("ix_taxa_is_extinct", "taxa", ["is_extinct"])


def downgrade() -> None:
    op.drop_index("ix_taxa_is_extinct")
    op.drop_column("taxa", "is_extinct")
