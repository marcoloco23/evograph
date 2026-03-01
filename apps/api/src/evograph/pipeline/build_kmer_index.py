"""Build FAISS k-mer index from canonical COI sequences.

Run as: python -m evograph.pipeline.build_kmer_index
"""

from __future__ import annotations

import argparse
import logging

from sqlalchemy import select

from evograph.db.models import Sequence
from evograph.db.session import SessionLocal
from evograph.services.kmer_index import build_faiss_index, save_index

logger = logging.getLogger(__name__)


def build() -> None:
    """Load canonical COI sequences and build FAISS k-mer index."""
    session = SessionLocal()
    try:
        rows = session.execute(
            select(Sequence).where(
                Sequence.is_canonical.is_(True),
                Sequence.marker == "COI",
            )
        ).scalars().all()

        sequences = {seq.ott_id: seq.sequence for seq in rows}
        logger.info("Loaded %d canonical COI sequences", len(sequences))

        if len(sequences) < 2:
            logger.warning("Need at least 2 sequences to build index, skipping")
            return

        index, ott_ids = build_faiss_index(sequences)
        save_index(index, ott_ids)
        logger.info("k-mer index built and saved successfully")

    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS k-mer index")
    parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    build()


if __name__ == "__main__":
    main()
