"""Taxon detail endpoint with paginated children."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from evograph.api.schemas.taxa import ChildrenPage, TaxonDetail, TaxonSummary
from evograph.db.models import NodeMedia, Sequence, Taxon
from evograph.db.session import get_db

router = APIRouter(tags=["taxa"])

_INLINE_CHILDREN_LIMIT = 100


@router.get("/taxa/{ott_id}", response_model=TaxonDetail)
def get_taxon(
    ott_id: int,
    db: Session = Depends(get_db),
) -> TaxonDetail:
    """Get taxon detail with children, lineage, and canonical sequence availability.

    For taxa with more than 100 children, only the first 100 are returned inline.
    Use GET /taxa/{ott_id}/children?offset=... for paginated access.
    """
    taxon = db.query(Taxon).filter(Taxon.ott_id == ott_id).first()
    if taxon is None:
        raise HTTPException(status_code=404, detail="Taxon not found")

    # Count total children
    total_children = (
        db.query(func.count(Taxon.ott_id))
        .filter(Taxon.parent_ott_id == ott_id)
        .scalar()
    ) or 0

    # Get children (limited for inline display)
    children = (
        db.query(Taxon)
        .filter(Taxon.parent_ott_id == ott_id)
        .order_by(Taxon.name)
        .limit(_INLINE_CHILDREN_LIMIT)
        .all()
    )

    # Batch child-count query: for each child, how many grandchildren?
    child_ids = [c.ott_id for c in children]
    child_counts: dict[int, int] = {}
    if child_ids:
        counts = (
            db.query(Taxon.parent_ott_id, func.count(Taxon.ott_id))
            .filter(Taxon.parent_ott_id.in_(child_ids))
            .group_by(Taxon.parent_ott_id)
            .all()
        )
        child_counts = {parent_id: cnt for parent_id, cnt in counts}

    # Batch image lookup for children
    child_images: dict[int, str] = {}
    if child_ids:
        media_rows = (
            db.query(NodeMedia.ott_id, NodeMedia.image_url)
            .filter(NodeMedia.ott_id.in_(child_ids))
            .all()
        )
        child_images = {ott: url for ott, url in media_rows}

    has_canonical = (
        db.query(Sequence)
        .filter(Sequence.ott_id == ott_id, Sequence.is_canonical.is_(True))
        .first()
        is not None
    )

    media = db.query(NodeMedia).filter(NodeMedia.ott_id == ott_id).first()

    # Build lineage by walking up the parent chain
    lineage: list[TaxonSummary] = []
    current = taxon
    seen = {ott_id}
    while current.parent_ott_id and current.parent_ott_id not in seen:
        seen.add(current.parent_ott_id)
        parent = db.query(Taxon).filter(Taxon.ott_id == current.parent_ott_id).first()
        if parent is None:
            break
        lineage.append(TaxonSummary(
            ott_id=parent.ott_id,
            name=parent.name,
            rank=parent.rank,
        ))
        current = parent
    lineage.reverse()  # root → ... → parent

    parent_name = None
    if lineage:
        parent_name = lineage[-1].name

    # Build wikipedia URL from name
    wikipedia_url = f"https://en.wikipedia.org/wiki/{taxon.name.replace(' ', '_')}"

    return TaxonDetail(
        ott_id=taxon.ott_id,
        name=taxon.name,
        rank=taxon.rank,
        parent_ott_id=taxon.parent_ott_id,
        parent_name=parent_name,
        ncbi_tax_id=taxon.ncbi_tax_id,
        children=[
            TaxonSummary(
                ott_id=c.ott_id,
                name=c.name,
                rank=c.rank,
                child_count=child_counts.get(c.ott_id, 0),
                image_url=child_images.get(c.ott_id),
            )
            for c in children
        ],
        total_children=total_children,
        has_canonical_sequence=has_canonical,
        image_url=media.image_url if media else None,
        lineage=lineage,
        wikipedia_url=wikipedia_url,
    )


@router.get("/taxa/{ott_id}/children", response_model=ChildrenPage)
def get_children(
    ott_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> ChildrenPage:
    """Paginated children for a taxon."""
    taxon = db.query(Taxon).filter(Taxon.ott_id == ott_id).first()
    if taxon is None:
        raise HTTPException(status_code=404, detail="Taxon not found")

    total = (
        db.query(func.count(Taxon.ott_id))
        .filter(Taxon.parent_ott_id == ott_id)
        .scalar()
    ) or 0

    children = (
        db.query(Taxon)
        .filter(Taxon.parent_ott_id == ott_id)
        .order_by(Taxon.name)
        .offset(offset)
        .limit(limit)
        .all()
    )

    child_ids = [c.ott_id for c in children]
    child_counts: dict[int, int] = {}
    child_images: dict[int, str] = {}

    if child_ids:
        counts = (
            db.query(Taxon.parent_ott_id, func.count(Taxon.ott_id))
            .filter(Taxon.parent_ott_id.in_(child_ids))
            .group_by(Taxon.parent_ott_id)
            .all()
        )
        child_counts = {parent_id: cnt for parent_id, cnt in counts}

        media_rows = (
            db.query(NodeMedia.ott_id, NodeMedia.image_url)
            .filter(NodeMedia.ott_id.in_(child_ids))
            .all()
        )
        child_images = {ott: url for ott, url in media_rows}

    return ChildrenPage(
        items=[
            TaxonSummary(
                ott_id=c.ott_id,
                name=c.name,
                rank=c.rank,
                child_count=child_counts.get(c.ott_id, 0),
                image_url=child_images.get(c.ott_id),
            )
            for c in children
        ],
        total=total,
        offset=offset,
        limit=limit,
    )
