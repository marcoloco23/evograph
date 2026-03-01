"""Backfill lineage arrays for all taxa using a recursive CTE.

The lineage column stores the ancestor chain as an int[] from root to parent.
This enables fast lineage lookups without recursive queries at read time.

Usage:
  conda run -n evograph python -m evograph.pipeline.backfill_lineage
"""

import logging

from sqlalchemy import text

from evograph.db.session import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def run() -> None:
    """Populate lineage arrays for all taxa in a single recursive CTE."""
    session = SessionLocal()
    try:
        # Use a recursive CTE to build lineage arrays bottom-up
        # Start from root nodes (parent_ott_id IS NULL), walk down
        log.info("Computing lineage arrays for all taxa...")
        result = session.execute(text("""
            WITH RECURSIVE lineage_cte AS (
                -- Base case: root nodes have empty lineage
                SELECT ott_id, parent_ott_id, ARRAY[]::int[] AS lineage
                FROM taxa
                WHERE parent_ott_id IS NULL

                UNION ALL

                -- Recursive case: append parent to lineage
                SELECT t.ott_id, t.parent_ott_id, lc.lineage || t.parent_ott_id
                FROM taxa t
                JOIN lineage_cte lc ON t.parent_ott_id = lc.ott_id
            )
            UPDATE taxa
            SET lineage = lineage_cte.lineage
            FROM lineage_cte
            WHERE taxa.ott_id = lineage_cte.ott_id
        """))
        session.commit()
        updated = result.rowcount
        log.info("Updated lineage for %d taxa", updated)

        # Verify
        null_count = session.execute(
            text("SELECT COUNT(*) FROM taxa WHERE lineage IS NULL")
        ).scalar()
        log.info("Remaining taxa with NULL lineage: %d", null_count)

    finally:
        session.close()


if __name__ == "__main__":
    run()
