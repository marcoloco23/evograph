"""Sequence endpoints for a taxon."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from evograph.api.schemas.sequence import SequenceOut
from evograph.db.models import Sequence, Taxon
from evograph.db.session import get_db

router = APIRouter(tags=["sequences"])


@router.get("/taxa/{ott_id}/sequences", response_model=list[SequenceOut])
def get_sequences(
    ott_id: int,
    db: Session = Depends(get_db),
) -> list[SequenceOut]:
    """Get all sequences for a taxon."""
    taxon = db.query(Taxon).filter(Taxon.ott_id == ott_id).first()
    if taxon is None:
        raise HTTPException(status_code=404, detail="Taxon not found")

    rows = (
        db.query(Sequence)
        .filter(Sequence.ott_id == ott_id)
        .order_by(Sequence.is_canonical.desc(), Sequence.retrieved_at.desc())
        .all()
    )
    return [
        SequenceOut(
            id=str(s.id),
            ott_id=s.ott_id,
            marker=s.marker,
            source=s.source,
            accession=s.accession,
            length=s.length,
            is_canonical=s.is_canonical,
            retrieved_at=s.retrieved_at,
        )
        for s in rows
    ]
