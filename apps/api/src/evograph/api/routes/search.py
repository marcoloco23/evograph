"""Search endpoint for taxa."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from evograph.api.schemas.taxa import TaxonSummary
from evograph.db.models import Taxon
from evograph.db.session import get_db

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[TaxonSummary])
def search_taxa(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
) -> list[TaxonSummary]:
    """Search taxa by name (case-insensitive ILIKE)."""
    rows = (
        db.query(Taxon)
        .filter(Taxon.name.ilike(f"%{q}%"))
        .order_by(Taxon.name)
        .limit(limit)
        .all()
    )
    return [
        TaxonSummary(ott_id=t.ott_id, name=t.name, rank=t.rank) for t in rows
    ]
