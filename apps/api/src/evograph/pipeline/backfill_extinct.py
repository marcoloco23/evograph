"""Backfill is_extinct flag from OpenTree taxonomy flags.

OpenTree's taxon_info API returns a 'flags' array that may include
'extinct' or 'extinct_inherited' for extinct taxa.

Usage:
  conda run -n evograph python -m evograph.pipeline.backfill_extinct
"""

import asyncio
import logging

from sqlalchemy import select, update

from evograph.db.models import Taxon
from evograph.db.session import SessionLocal
from evograph.services.ott_client import OpenTreeClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BATCH_SIZE = 50
EXTINCT_FLAGS = {"extinct", "extinct_inherited"}


async def _fetch_extinct_batch(
    client: OpenTreeClient, ott_ids: list[int]
) -> dict[int, bool]:
    """Query OpenTree for a batch of OTT IDs, return {ott_id: is_extinct}."""
    tasks = [client.taxon_info(ott_id) for ott_id in ott_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    extinct_map: dict[int, bool] = {}
    for ott_id, result in zip(ott_ids, results):
        if isinstance(result, Exception):
            continue
        flags = set(result.get("flags", []))
        extinct_map[ott_id] = bool(flags & EXTINCT_FLAGS)
    return extinct_map


async def run() -> None:
    """Backfill is_extinct for all taxa where it's currently NULL."""
    session = SessionLocal()
    try:
        # Get all taxa without is_extinct set
        rows = session.execute(
            select(Taxon.ott_id).where(Taxon.is_extinct.is_(None))
        ).scalars().all()
        ott_ids = list(rows)
        log.info("Found %d taxa with is_extinct=NULL", len(ott_ids))

        if not ott_ids:
            log.info("Nothing to backfill")
            return

        client = OpenTreeClient()
        extinct_count = 0
        extant_count = 0

        for i in range(0, len(ott_ids), BATCH_SIZE):
            batch = ott_ids[i : i + BATCH_SIZE]
            extinct_map = await _fetch_extinct_batch(client, batch)

            for ott_id, is_extinct in extinct_map.items():
                session.execute(
                    update(Taxon)
                    .where(Taxon.ott_id == ott_id)
                    .values(is_extinct=is_extinct)
                )
                if is_extinct:
                    extinct_count += 1
                else:
                    extant_count += 1

            session.commit()
            done = min(i + BATCH_SIZE, len(ott_ids))
            if done % 500 == 0 or done == len(ott_ids):
                log.info(
                    "  Processed %d / %d (extinct: %d, extant: %d)",
                    done, len(ott_ids), extinct_count, extant_count,
                )

        log.info(
            "Done: %d extinct, %d extant out of %d total",
            extinct_count, extant_count, len(ott_ids),
        )
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(run())
