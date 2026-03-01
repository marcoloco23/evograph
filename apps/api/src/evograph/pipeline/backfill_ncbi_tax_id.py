"""Backfill ncbi_tax_id for taxa in the database.

Queries the NCBI Taxonomy E-utilities API to resolve species/genus names
to NCBI taxonomy IDs and updates the taxa table.

Run as: python -m evograph.pipeline.backfill_ncbi_tax_id [--limit N] [--batch N]
"""

from __future__ import annotations

import argparse
import asyncio
import logging

import httpx
from sqlalchemy import select, update

from evograph.db.models import Taxon
from evograph.db.session import SessionLocal

logger = logging.getLogger(__name__)

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


async def _lookup_tax_id(
    client: httpx.AsyncClient, name: str
) -> int | None:
    """Look up NCBI taxonomy ID for a given taxon name.

    Uses esearch against the NCBI Taxonomy database.
    Returns the taxonomy ID if exactly one match is found, else None.
    """
    resp = await client.get(
        f"{NCBI_BASE}/esearch.fcgi",
        params={
            "db": "taxonomy",
            "term": f'"{name}"[Scientific Name]',
            "retmode": "json",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    id_list = data.get("esearchresult", {}).get("idlist", [])

    if len(id_list) == 1:
        return int(id_list[0])
    return None


async def backfill(limit: int | None = None, batch_size: int = 50) -> None:
    """Look up and backfill ncbi_tax_id for taxa that don't have one."""
    session = SessionLocal()

    try:
        # Find taxa without ncbi_tax_id
        stmt = (
            select(Taxon)
            .where(Taxon.ncbi_tax_id.is_(None))
            .order_by(Taxon.ott_id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        taxa = session.execute(stmt).scalars().all()
        logger.info("Found %d taxa without ncbi_tax_id", len(taxa))

        if not taxa:
            return

        resolved = 0
        failed = 0

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for i, taxon in enumerate(taxa):
                try:
                    tax_id = await _lookup_tax_id(client, taxon.name)

                    if tax_id is not None:
                        session.execute(
                            update(Taxon)
                            .where(Taxon.ott_id == taxon.ott_id)
                            .values(ncbi_tax_id=tax_id)
                        )
                        resolved += 1

                    if (i + 1) % batch_size == 0:
                        session.commit()
                        logger.info(
                            "  [%d/%d] Resolved %d, failed %d",
                            i + 1, len(taxa), resolved, failed,
                        )

                except Exception:
                    failed += 1
                    logger.exception(
                        "  Error looking up %s (ott_id=%d)", taxon.name, taxon.ott_id
                    )

                # NCBI rate limit: max 3 requests/second without API key
                await asyncio.sleep(0.4)

        session.commit()
        logger.info(
            "Backfill complete: %d resolved, %d failed, %d total",
            resolved, failed, len(taxa),
        )

    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill NCBI taxonomy IDs")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of taxa to process",
    )
    parser.add_argument(
        "--batch", type=int, default=50,
        help="Commit after every N lookups (default: 50)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(backfill(limit=args.limit, batch_size=args.batch))


if __name__ == "__main__":
    main()
