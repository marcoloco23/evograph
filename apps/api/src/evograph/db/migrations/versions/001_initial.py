"""Initial schema: taxa, sequences, edges, node_media.

Revision ID: 001
Revises: None
Create Date: 2026-02-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "taxa",
        sa.Column("ott_id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("rank", sa.Text, nullable=False),
        sa.Column(
            "parent_ott_id",
            sa.Integer,
            sa.ForeignKey("taxa.ott_id"),
            nullable=True,
        ),
        sa.Column("lineage", ARRAY(sa.Integer), nullable=True),
        sa.Column("ncbi_tax_id", sa.Integer, nullable=True),
        sa.Column("bold_tax_id", sa.Text, nullable=True),
        sa.Column("synonyms", JSONB, nullable=True),
    )
    op.create_index("ix_taxa_name", "taxa", ["name"])
    op.create_index("ix_taxa_parent_ott_id", "taxa", ["parent_ott_id"])

    op.create_table(
        "sequences",
        sa.Column(
            "id",
            sa.Uuid,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "ott_id",
            sa.Integer,
            sa.ForeignKey("taxa.ott_id"),
            nullable=False,
        ),
        sa.Column("marker", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("accession", sa.Text, nullable=False),
        sa.Column("sequence", sa.Text, nullable=False),
        sa.Column("length", sa.Integer, nullable=False),
        sa.Column("quality", JSONB, nullable=True),
        sa.Column("is_canonical", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "retrieved_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_sequences_ott_id", "sequences", ["ott_id"])

    op.create_table(
        "edges",
        sa.Column(
            "src_ott_id",
            sa.Integer,
            sa.ForeignKey("taxa.ott_id"),
            nullable=False,
        ),
        sa.Column(
            "dst_ott_id",
            sa.Integer,
            sa.ForeignKey("taxa.ott_id"),
            nullable=False,
        ),
        sa.Column("marker", sa.Text, nullable=False),
        sa.Column("distance", sa.Double, nullable=False),
        sa.Column("mi_norm", sa.Double, nullable=False),
        sa.Column("align_len", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("src_ott_id", "dst_ott_id", "marker"),
    )
    op.create_index("ix_edges_src_ott_id", "edges", ["src_ott_id"])
    op.create_index("ix_edges_dst_ott_id", "edges", ["dst_ott_id"])

    op.create_table(
        "node_media",
        sa.Column(
            "ott_id",
            sa.Integer,
            sa.ForeignKey("taxa.ott_id"),
            primary_key=True,
        ),
        sa.Column("image_url", sa.Text, nullable=False),
        sa.Column("attribution", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("node_media")
    op.drop_table("edges")
    op.drop_table("sequences")
    op.drop_table("taxa")
