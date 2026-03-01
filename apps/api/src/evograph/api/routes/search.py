"""Search endpoint for taxa.

Uses ILIKE for substring matching, backed by a pg_trgm GIN index
(migration 002) for O(1) lookup instead of sequential scan.

Results are ordered to prioritize:
1. Prefix matches (names starting with the query)
2. Alphabetical order for remaining matches
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from evograph.api.schemas.taxa import SearchPage, TaxonSummary
from evograph.db.models import Taxon
from evograph.db.session import get_db

router = APIRouter(tags=["search"])


def _escape_like(s: str) -> str:
    """Escape special LIKE/ILIKE characters to prevent pattern injection."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/search", response_model=SearchPage)
def search_taxa(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
) -> SearchPage:
    """Search taxa by name (case-insensitive substring match).

    Uses pg_trgm GIN index for fast ILIKE on large tables.
    Results prioritize prefix matches over substring matches.
    Returns paginated response with total count.
    """
    escaped = _escape_like(q)

    base_filter = Taxon.name.ilike(f"%{escaped}%")

    # Total matching count (for client to know if there are more results)
    total = db.query(func.count(Taxon.ott_id)).filter(base_filter).scalar() or 0

    # Prefix matches rank first (sort_key=0), substring matches second (sort_key=1)
    prefix_case = case(
        (Taxon.name.ilike(f"{escaped}%"), 0),
        else_=1,
    )

    rows = (
        db.query(Taxon)
        .filter(base_filter)
        .order_by(prefix_case, Taxon.name)
        .limit(limit)
        .all()
    )
    return SearchPage(
        items=[
            TaxonSummary(ott_id=t.ott_id, name=t.name, rank=t.rank, is_extinct=t.is_extinct) for t in rows
        ],
        total=total,
        limit=limit,
    )
