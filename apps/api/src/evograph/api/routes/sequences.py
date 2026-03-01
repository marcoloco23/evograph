"""Sequence endpoints for a taxon."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from evograph.api.schemas.sequence import SequenceOut, SequencePage
from evograph.db.models import Sequence, Taxon
from evograph.db.session import get_db

router = APIRouter(tags=["sequences"])


@router.get("/taxa/{ott_id}/sequences", response_model=SequencePage)
def get_sequences(
    ott_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> SequencePage:
    """Get paginated sequences for a taxon."""
    taxon = db.query(Taxon).filter(Taxon.ott_id == ott_id).first()
    if taxon is None:
        raise HTTPException(status_code=404, detail="Taxon not found")

    total = (
        db.query(func.count(Sequence.id))
        .filter(Sequence.ott_id == ott_id)
        .scalar()
    ) or 0

    rows = (
        db.query(Sequence)
        .filter(Sequence.ott_id == ott_id)
        .order_by(Sequence.is_canonical.desc(), Sequence.retrieved_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return SequencePage(
        items=[
            SequenceOut(
                id=str(s.id),
                ott_id=s.ott_id,
                marker=s.marker,
                source=s.source,
                accession=s.accession,
                sequence=s.sequence,
                length=s.length,
                is_canonical=s.is_canonical,
                retrieved_at=s.retrieved_at,
            )
            for s in rows
        ],
        total=total,
        offset=offset,
        limit=limit,
    )
