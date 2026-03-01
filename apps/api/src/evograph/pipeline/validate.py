"""Validation checks for the graph data.

- % of MI-neighbors sharing genus
- % sharing family
- Distance distribution stats
- Outlier flagging (cross-family close neighbors, within-genus distant pairs)

Run as: python -m evograph.pipeline.validate [--output report.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
from dataclasses import dataclass, field

from sqlalchemy import select

from evograph.db.models import Edge, Taxon
from evograph.db.session import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class OutlierRecord:
    """A single outlier edge with context."""

    src_ott_id: int
    src_name: str
    dst_ott_id: int
    dst_name: str
    distance: float
    reason: str  # "cross_family_close" or "within_genus_distant"


@dataclass
class ValidationReport:
    """Structured validation results."""

    total_edges: int = 0
    same_genus_count: int = 0
    same_family_count: int = 0
    same_genus_pct: float = 0.0
    same_family_pct: float = 0.0
    distance_min: float = 0.0
    distance_max: float = 0.0
    distance_mean: float = 0.0
    distance_median: float = 0.0
    distance_stdev: float | None = None
    outliers: list[OutlierRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_edges": self.total_edges,
            "taxonomy_coherence": {
                "same_genus": self.same_genus_count,
                "same_family": self.same_family_count,
                "same_genus_pct": round(self.same_genus_pct, 2),
                "same_family_pct": round(self.same_family_pct, 2),
            },
            "distance_distribution": {
                "min": round(self.distance_min, 4),
                "max": round(self.distance_max, 4),
                "mean": round(self.distance_mean, 4),
                "median": round(self.distance_median, 4),
                "stdev": round(self.distance_stdev, 4) if self.distance_stdev is not None else None,
            },
            "outliers": {
                "cross_family_close": [
                    {
                        "src_ott_id": o.src_ott_id,
                        "src_name": o.src_name,
                        "dst_ott_id": o.dst_ott_id,
                        "dst_name": o.dst_name,
                        "distance": round(o.distance, 4),
                    }
                    for o in self.outliers
                    if o.reason == "cross_family_close"
                ],
                "within_genus_distant": [
                    {
                        "src_ott_id": o.src_ott_id,
                        "src_name": o.src_name,
                        "dst_ott_id": o.dst_ott_id,
                        "dst_name": o.dst_name,
                        "distance": round(o.distance, 4),
                    }
                    for o in self.outliers
                    if o.reason == "within_genus_distant"
                ],
            },
        }


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


def compute_validation_report(session) -> ValidationReport | None:
    """Compute validation report from the database.

    Returns a ValidationReport, or None if no edges exist.
    """
    all_taxa = session.execute(select(Taxon)).scalars().all()
    taxa_by_id = {t.ott_id: t for t in all_taxa}
    logger.info("Loaded %d taxa", len(taxa_by_id))

    edges = session.execute(select(Edge)).scalars().all()
    logger.info("Loaded %d edges", len(edges))

    if not edges:
        return None

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
    outliers: list[OutlierRecord] = []

    for e in edges:
        src_genus = genus_of.get(e.src_ott_id)
        dst_genus = genus_of.get(e.dst_ott_id)
        src_family = family_of.get(e.src_ott_id)
        dst_family = family_of.get(e.dst_ott_id)

        if src_genus is not None and src_genus == dst_genus:
            same_genus += 1
        if src_family is not None and src_family == dst_family:
            same_family += 1

        # Cross-family close neighbors (suspiciously similar across families)
        if e.distance < 0.05 and (
            src_family is None
            or dst_family is None
            or src_family != dst_family
        ):
            src_t = taxa_by_id.get(e.src_ott_id)
            dst_t = taxa_by_id.get(e.dst_ott_id)
            outliers.append(OutlierRecord(
                src_ott_id=e.src_ott_id,
                src_name=getattr(src_t, "name", str(e.src_ott_id)),
                dst_ott_id=e.dst_ott_id,
                dst_name=getattr(dst_t, "name", str(e.dst_ott_id)),
                distance=e.distance,
                reason="cross_family_close",
            ))

        # Within-genus distant pairs (unexpectedly different within same genus)
        if e.distance > 0.8 and (
            src_genus is not None
            and dst_genus is not None
            and src_genus == dst_genus
        ):
            src_t = taxa_by_id.get(e.src_ott_id)
            dst_t = taxa_by_id.get(e.dst_ott_id)
            outliers.append(OutlierRecord(
                src_ott_id=e.src_ott_id,
                src_name=getattr(src_t, "name", str(e.src_ott_id)),
                dst_ott_id=e.dst_ott_id,
                dst_name=getattr(dst_t, "name", str(e.dst_ott_id)),
                distance=e.distance,
                reason="within_genus_distant",
            ))

    report = ValidationReport(
        total_edges=total,
        same_genus_count=same_genus,
        same_family_count=same_family,
        same_genus_pct=100.0 * same_genus / total,
        same_family_pct=100.0 * same_family / total,
        distance_min=min(distances),
        distance_max=max(distances),
        distance_mean=statistics.mean(distances),
        distance_median=statistics.median(distances),
        distance_stdev=statistics.stdev(distances) if len(distances) >= 2 else None,
        outliers=outliers,
    )

    return report


def _print_report(report: ValidationReport) -> None:
    """Pretty-print a validation report to stdout."""
    cross_family = [o for o in report.outliers if o.reason == "cross_family_close"]
    within_genus = [o for o in report.outliers if o.reason == "within_genus_distant"]

    print("=" * 60)
    print("EvoGraph Validation Report")
    print("=" * 60)

    print(f"\nTotal edges: {report.total_edges}")
    print(
        f"Neighbors sharing genus:  {report.same_genus_count:>6d} / {report.total_edges} "
        f"({report.same_genus_pct:.1f}%)"
    )
    print(
        f"Neighbors sharing family: {report.same_family_count:>6d} / {report.total_edges} "
        f"({report.same_family_pct:.1f}%)"
    )

    print("\nDistance distribution:")
    print(f"  Min:    {report.distance_min:.4f}")
    print(f"  Max:    {report.distance_max:.4f}")
    print(f"  Mean:   {report.distance_mean:.4f}")
    print(f"  Median: {report.distance_median:.4f}")
    if report.distance_stdev is not None:
        print(f"  StdDev: {report.distance_stdev:.4f}")

    print("\nOutliers:")
    print(f"  Distance < 0.05 across families: {len(cross_family)}")
    for o in cross_family[:10]:
        print(f"    {o.src_name} <-> {o.dst_name}  dist={o.distance:.4f}")
    if len(cross_family) > 10:
        print(f"    ... and {len(cross_family) - 10} more")

    print(f"  Distance > 0.8 within same genus: {len(within_genus)}")
    for o in within_genus[:10]:
        print(f"    {o.src_name} <-> {o.dst_name}  dist={o.distance:.4f}")
    if len(within_genus) > 10:
        print(f"    ... and {len(within_genus) - 10} more")

    print("=" * 60)


def validate(output_path: str | None = None) -> None:
    """Run all validation checks, print results, and optionally save to JSON."""
    session = SessionLocal()
    try:
        report = compute_validation_report(session)

        if report is None:
            logger.warning("No edges found. Nothing to validate.")
            return

        _print_report(report)

        if output_path:
            with open(output_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            print(f"\nReport saved to {output_path}")

    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate EvoGraph data quality")
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Save report as JSON to this path",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    validate(output_path=args.output)
