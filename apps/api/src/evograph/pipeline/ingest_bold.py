"""Ingest COI sequences from BOLD for species in the DB.

Run as: python -m evograph.pipeline.ingest_bold [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from evograph.db.models import Sequence, Taxon
from evograph.db.session import SessionLocal
from evograph.services.bold_client import BoldClient

logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw/bold")
_NON_ACGTN = re.compile(r"[^ACGTN]")
MIN_SEQ_LEN = 400


def _clean_seq(raw: str) -> str:
    return _NON_ACGTN.sub("", raw.upper())


async def ingest(limit: int | None = None) -> None:
    """Run the BOLD ingestion pipeline."""
    session = SessionLocal()
    bold = BoldClient()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    try:
        stmt = select(Taxon).where(Taxon.rank == "species")
        if limit is not None:
            stmt = stmt.limit(limit)
        taxa = session.execute(stmt).scalars().all()
        logger.info("Found %d species-rank taxa to process", len(taxa))

        total_stored = 0
        for i, taxon in enumerate(taxa):
            try:
                logger.info(
                    "[%d/%d] Fetching BOLD sequences for %s (ott_id=%d)",
                    i + 1, len(taxa), taxon.name, taxon.ott_id,
                )
                records = await bold.fetch_sequences(taxon.name)

                # Save raw JSONL
                raw_path = RAW_DIR / f"{taxon.ott_id}.jsonl"
                raw_path.write_text(
                    "\n".join(json.dumps(r) for r in records),
                    encoding="utf-8",
                )

                count = 0
                for rec in records:
                    nuc = rec.get("nuc", "")
                    if not nuc:
                        continue
                    seq = _clean_seq(nuc)
                    if len(seq) < MIN_SEQ_LEN:
                        continue

                    accession = rec.get("processid") or rec.get("sampleid") or str(uuid.uuid4())
                    ambig = seq.count("N")

                    stmt_ins = pg_insert(Sequence).values(
                        id=uuid.uuid4(),
                        ott_id=taxon.ott_id,
                        marker="COI",
                        source="BOLD",
                        accession=accession,
                        sequence=seq,
                        length=len(seq),
                        quality={"ambig": ambig},
                        is_canonical=False,
                    ).on_conflict_do_nothing()
                    session.execute(stmt_ins)
                    count += 1

                session.commit()
                total_stored += count
                if count:
                    logger.info("  Stored %d sequences for %s", count, taxon.name)
                else:
                    logger.info("  No valid sequences for %s", taxon.name)

            except Exception:
                session.rollback()
                logger.exception(
                    "  Error processing %s (ott_id=%d)", taxon.name, taxon.ott_id
                )

            # Rate limiting
            await asyncio.sleep(0.5)

        logger.info("BOLD ingestion complete. Total sequences stored: %d", total_stored)

    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest BOLD COI sequences")
    parser.add_argument("--limit", type=int, default=None, help="Max number of taxa to process")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(ingest(limit=args.limit))


if __name__ == "__main__":
    main()
