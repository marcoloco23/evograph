"""Stats endpoint for observability — database counts and data quality overview."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from evograph.db.models import Edge, Sequence, Taxon
from evograph.db.session import get_db

router = APIRouter(tags=["stats"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Return summary statistics about the database contents.

    Includes:
    - Total taxa count and breakdown by rank
    - Total sequences and breakdown by source/marker
    - Total MI edges with distance summary
    - Species with/without sequences
    """
    # Taxa by rank
    rank_counts = (
        db.query(Taxon.rank, func.count())
        .group_by(Taxon.rank)
        .order_by(func.count().desc())
        .all()
    )

    total_taxa = sum(c for _, c in rank_counts)

    # Sequences by source
    seq_by_source = (
        db.query(Sequence.source, func.count())
        .group_by(Sequence.source)
        .all()
    )
    total_sequences = sum(c for _, c in seq_by_source)

    # Species with at least one sequence
    species_with_seqs = (
        db.query(func.count(func.distinct(Sequence.ott_id)))
        .scalar()
    ) or 0

    total_species = next(
        (c for r, c in rank_counts if r == "species"), 0
    )

    # Edge stats
    total_edges = db.query(func.count()).select_from(Edge).scalar() or 0
    distance_stats = None
    if total_edges > 0:
        row = db.query(
            func.min(Edge.distance),
            func.max(Edge.distance),
            func.avg(Edge.distance),
        ).one()
        distance_stats = {
            "min": round(float(row[0]), 4) if row[0] is not None else None,
            "max": round(float(row[1]), 4) if row[1] is not None else None,
            "avg": round(float(row[2]), 4) if row[2] is not None else None,
        }

    data = {
        "taxa": {
            "total": total_taxa,
            "by_rank": {rank: count for rank, count in rank_counts},
        },
        "sequences": {
            "total": total_sequences,
            "by_source": {source: count for source, count in seq_by_source},
            "species_with_sequences": species_with_seqs,
            "species_total": total_species,
            "coverage_pct": (
                round(100.0 * species_with_seqs / total_species, 1)
                if total_species > 0 else 0.0
            ),
        },
        "edges": {
            "total": total_edges,
            "distance": distance_stats,
        },
    }
    return JSONResponse(content=data, headers={"Cache-Control": "public, max-age=60"})
