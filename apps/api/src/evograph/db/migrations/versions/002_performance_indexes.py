"""Add performance indexes for search, neighbors, and canonical lookups.

Revision ID: 002
Revises: 001
Create Date: 2026-03-01

Indexes added:
- pg_trgm GIN index on taxa.name for fast ILIKE substring search
- Composite index on edges(src_ott_id, distance) for neighbor queries
- Composite index on sequences(ott_id, is_canonical) for canonical checks
- Index on taxa(rank) for rank-based filtering at scale
- Index on sequences(ott_id, marker, is_canonical) covering canonical selection
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pg_trgm extension for trigram similarity search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # GIN trigram index on taxa.name — enables fast ILIKE '%query%' search
    # Without this, ILIKE does a full sequential scan on large tables
    op.execute(
        "CREATE INDEX ix_taxa_name_trgm ON taxa USING gin (name gin_trgm_ops)"
    )

    # Composite index for neighbor queries:
    # SELECT ... FROM edges WHERE src_ott_id = ? ORDER BY distance LIMIT k
    op.create_index(
        "ix_edges_src_distance",
        "edges",
        ["src_ott_id", "distance"],
    )

    # Composite index for canonical sequence checks:
    # SELECT ... FROM sequences WHERE ott_id = ? AND is_canonical = true
    op.create_index(
        "ix_sequences_ott_canonical",
        "sequences",
        ["ott_id", "is_canonical"],
    )

    # Covering index for canonical selection pipeline:
    # SELECT ... FROM sequences WHERE ott_id = ? AND marker = 'COI'
    op.create_index(
        "ix_sequences_ott_marker",
        "sequences",
        ["ott_id", "marker"],
    )

    # Rank index for filtering/grouping by taxonomic rank
    op.create_index("ix_taxa_rank", "taxa", ["rank"])


def downgrade() -> None:
    op.drop_index("ix_taxa_rank")
    op.drop_index("ix_sequences_ott_marker")
    op.drop_index("ix_sequences_ott_canonical")
    op.drop_index("ix_edges_src_distance")
    op.execute("DROP INDEX IF EXISTS ix_taxa_name_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
