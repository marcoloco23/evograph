"""Deduplicate sequences by accession.

When the same accession appears multiple times (e.g., from multiple ingestion
runs or overlapping genus-level fetches), keep only the longest sequence per
(ott_id, accession, marker) tuple and remove the rest.

Run as: python -m evograph.pipeline.dedup_sequences [--dry-run]
"""

from __future__ import annotations

import argparse
import logging

from sqlalchemy import delete, func, select

from evograph.db.models import Sequence
from evograph.db.session import SessionLocal

logger = logging.getLogger(__name__)


def find_duplicates(session) -> list[tuple[int, str, str, int]]:
    """Find (ott_id, accession, marker) tuples with duplicate entries.

    Returns list of (ott_id, accession, marker, count) tuples.
    """
    stmt = (
        select(
            Sequence.ott_id,
            Sequence.accession,
            Sequence.marker,
            func.count().label("cnt"),
        )
        .group_by(Sequence.ott_id, Sequence.accession, Sequence.marker)
        .having(func.count() > 1)
    )
    return session.execute(stmt).all()


def dedup_sequences(dry_run: bool = False) -> None:
    """Remove duplicate sequences, keeping the longest per (ott_id, accession, marker)."""
    session = SessionLocal()

    try:
        dupes = find_duplicates(session)
        logger.info("Found %d (ott_id, accession, marker) groups with duplicates", len(dupes))

        if not dupes:
            logger.info("No duplicates found. Nothing to do.")
            return

        total_removed = 0
        for ott_id, accession, marker, cnt in dupes:
            # Get all sequences for this tuple, ordered by length desc
            seqs = (
                session.execute(
                    select(Sequence)
                    .where(
                        Sequence.ott_id == ott_id,
                        Sequence.accession == accession,
                        Sequence.marker == marker,
                    )
                    .order_by(Sequence.length.desc())
                )
                .scalars()
                .all()
            )

            # Keep the first (longest), remove the rest
            keep = seqs[0]
            to_remove = seqs[1:]

            if dry_run:
                logger.info(
                    "  [DRY RUN] ott_id=%d accession=%s: keep id=%s (len=%d), "
                    "would remove %d duplicates",
                    ott_id, accession, keep.id, keep.length, len(to_remove),
                )
            else:
                ids_to_delete = [s.id for s in to_remove]
                session.execute(
                    delete(Sequence).where(Sequence.id.in_(ids_to_delete))
                )
                total_removed += len(to_remove)

        if not dry_run:
            session.commit()

        logger.info(
            "Deduplication complete. %s %d duplicate sequences from %d groups.",
            "Would remove" if dry_run else "Removed",
            total_removed if not dry_run else sum(c - 1 for _, _, _, c in dupes),
            len(dupes),
        )

    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate sequences by accession")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report duplicates without removing them",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    dedup_sequences(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
