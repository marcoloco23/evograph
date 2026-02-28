"""Validation checks for the graph data.

- % of MI-neighbors sharing genus
- % sharing family
- Distance distribution stats
- Outlier flagging

Run as: python -m evograph.pipeline.validate
"""

from __future__ import annotations

import logging
import statistics

from sqlalchemy import select

from evograph.db.models import Edge, Taxon
from evograph.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _walk_to_rank(
    ott_id: int, target_rank: str, taxa_by_id: dict[int, Taxon]
) -> int | None:
    """Walk up the taxonomy tree from ott_id until reaching target_rank.

    Returns the ott_id of the ancestor at that rank, or None.
    """
    seen: set[int] = set()
    current_id: int | None = ott_id

    while current_id is not None and current_id not in seen:
        seen.add(current_id)
        taxon = taxa_by_id.get(current_id)
        if taxon is None:
            return None
        if taxon.rank == target_rank:
            return taxon.ott_id
        current_id = taxon.parent_ott_id

    return None


def validate() -> None:
    """Run all validation checks and print results."""
    session = SessionLocal()
    try:
        # Load taxa
        all_taxa = session.execute(select(Taxon)).scalars().all()
        taxa_by_id = {t.ott_id: t for t in all_taxa}
        logger.info("Loaded %d taxa", len(taxa_by_id))

        # Load edges
        edges = session.execute(select(Edge)).scalars().all()
        logger.info("Loaded %d edges", len(edges))

        if not edges:
            logger.warning("No edges found. Nothing to validate.")
            return

        # Build genus/family lookup for each species
        genus_of: dict[int, int | None] = {}
        family_of: dict[int, int | None] = {}

        relevant_ids = set()
        for e in edges:
            relevant_ids.add(e.src_ott_id)
            relevant_ids.add(e.dst_ott_id)

        for ott_id in relevant_ids:
            genus_of[ott_id] = _walk_to_rank(ott_id, "genus", taxa_by_id)
            family_of[ott_id] = _walk_to_rank(ott_id, "family", taxa_by_id)

        # Compute stats
        distances = [e.distance for e in edges]
        same_genus = 0
        same_family = 0
        total = len(edges)

        outliers_low: list[Edge] = []  # distance < 0.05, different families
        outliers_high: list[Edge] = []  # distance > 0.8, same genus

        for e in edges:
            src_genus = genus_of.get(e.src_ott_id)
            dst_genus = genus_of.get(e.dst_ott_id)
            src_family = family_of.get(e.src_ott_id)
            dst_family = family_of.get(e.dst_ott_id)

            if src_genus is not None and src_genus == dst_genus:
                same_genus += 1
            if src_family is not None and src_family == dst_family:
                same_family += 1

            # Outlier detection
            if e.distance < 0.05 and (
                src_family is None
                or dst_family is None
                or src_family != dst_family
            ):
                outliers_low.append(e)
            if e.distance > 0.8 and (
                src_genus is not None
                and dst_genus is not None
                and src_genus == dst_genus
            ):
                outliers_high.append(e)

        # Print results
        print("=" * 60)
        print("EvoGraph Validation Report")
        print("=" * 60)

        print(f"\nTotal edges: {total}")
        print(
            f"Neighbors sharing genus:  {same_genus:>6d} / {total} "
            f"({100.0 * same_genus / total:.1f}%)"
        )
        print(
            f"Neighbors sharing family: {same_family:>6d} / {total} "
            f"({100.0 * same_family / total:.1f}%)"
        )

        print("\nDistance distribution:")
        print(f"  Min:    {min(distances):.4f}")
        print(f"  Max:    {max(distances):.4f}")
        print(f"  Mean:   {statistics.mean(distances):.4f}")
        print(f"  Median: {statistics.median(distances):.4f}")
        if len(distances) >= 2:
            print(f"  StdDev: {statistics.stdev(distances):.4f}")

        print(f"\nOutliers:")
        print(
            f"  Distance < 0.05 across families: {len(outliers_low)}"
        )
        for e in outliers_low[:10]:
            src_name = taxa_by_id.get(e.src_ott_id)
            dst_name = taxa_by_id.get(e.dst_ott_id)
            print(
                f"    {getattr(src_name, 'name', e.src_ott_id)} <-> "
                f"{getattr(dst_name, 'name', e.dst_ott_id)}  "
                f"dist={e.distance:.4f}"
            )
        if len(outliers_low) > 10:
            print(f"    ... and {len(outliers_low) - 10} more")

        print(
            f"  Distance > 0.8 within same genus: {len(outliers_high)}"
        )
        for e in outliers_high[:10]:
            src_name = taxa_by_id.get(e.src_ott_id)
            dst_name = taxa_by_id.get(e.dst_ott_id)
            print(
                f"    {getattr(src_name, 'name', e.src_ott_id)} <-> "
                f"{getattr(dst_name, 'name', e.dst_ott_id)}  "
                f"dist={e.distance:.4f}"
            )
        if len(outliers_high) > 10:
            print(f"    ... and {len(outliers_high) - 10} more")

        print("=" * 60)

    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    validate()
