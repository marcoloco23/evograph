"""Taxon detail endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from evograph.api.schemas.taxa import TaxonDetail, TaxonSummary
from evograph.db.models import NodeMedia, Sequence, Taxon
from evograph.db.session import get_db

router = APIRouter(tags=["taxa"])


@router.get("/taxa/{ott_id}", response_model=TaxonDetail)
def get_taxon(
    ott_id: int,
    db: Session = Depends(get_db),
) -> TaxonDetail:
    """Get taxon detail with children and canonical sequence availability."""
    taxon = db.query(Taxon).filter(Taxon.ott_id == ott_id).first()
    if taxon is None:
        raise HTTPException(status_code=404, detail="Taxon not found")

    children = (
        db.query(Taxon)
        .filter(Taxon.parent_ott_id == ott_id)
        .order_by(Taxon.name)
        .all()
    )

    has_canonical = (
        db.query(Sequence)
        .filter(Sequence.ott_id == ott_id, Sequence.is_canonical.is_(True))
        .first()
        is not None
    )

    media = db.query(NodeMedia).filter(NodeMedia.ott_id == ott_id).first()

    parent_name = None
    if taxon.parent_ott_id:
        parent = db.query(Taxon).filter(Taxon.ott_id == taxon.parent_ott_id).first()
        parent_name = parent.name if parent else None

    return TaxonDetail(
        ott_id=taxon.ott_id,
        name=taxon.name,
        rank=taxon.rank,
        parent_ott_id=taxon.parent_ott_id,
        parent_name=parent_name,
        ncbi_tax_id=taxon.ncbi_tax_id,
        children=[
            TaxonSummary(ott_id=c.ott_id, name=c.name, rank=c.rank)
            for c in children
        ],
        has_canonical_sequence=has_canonical,
        image_url=media.image_url if media else None,
    )
