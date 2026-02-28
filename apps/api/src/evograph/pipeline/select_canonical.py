"""Select one canonical COI sequence per taxon.

Scoring: length - 10 * ambig_count.  Highest score wins.

Run as: python -m evograph.pipeline.select_canonical
"""

from __future__ import annotations

import logging

from sqlalchemy import distinct, select, update

from evograph.db.models import Sequence
from evograph.db.session import SessionLocal

logger = logging.getLogger(__name__)


def select_canonical() -> None:
    """For each ott_id with COI sequences, mark the best one as canonical."""
    session = SessionLocal()
    try:
        # Get distinct ott_ids that have sequences
        ott_ids = (
            session.execute(
                select(distinct(Sequence.ott_id)).where(Sequence.marker == "COI")
            )
            .scalars()
            .all()
        )
        logger.info("Processing %d taxa with COI sequences", len(ott_ids))

        for ott_id in ott_ids:
            seqs = (
                session.execute(
                    select(Sequence).where(
                        Sequence.ott_id == ott_id, Sequence.marker == "COI"
                    )
                )
                .scalars()
                .all()
            )

            if not seqs:
                continue

            # Score each sequence: length - 10 * ambig_count
            best = max(seqs, key=lambda s: _score(s))

            # Reset all to non-canonical, then set the best
            session.execute(
                update(Sequence)
                .where(Sequence.ott_id == ott_id, Sequence.marker == "COI")
                .values(is_canonical=False)
            )
            session.execute(
                update(Sequence)
                .where(Sequence.id == best.id)
                .values(is_canonical=True)
            )
            session.commit()

        logger.info("Done. Selected canonical sequences for %d taxa.", len(ott_ids))

    finally:
        session.close()


def _score(seq: Sequence) -> float:
    """Score a sequence for canonical selection."""
    ambig = 0
    if seq.quality and isinstance(seq.quality, dict):
        ambig = seq.quality.get("ambig", 0)
    return seq.length - 10 * ambig


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    select_canonical()
