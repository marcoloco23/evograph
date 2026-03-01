"""Browse species endpoint with filtering and pagination."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from evograph.api.schemas.taxa import SpeciesBrowsePage, SpeciesSummary
from evograph.db.models import Edge, NodeMedia, Sequence, Taxon
from evograph.db.session import get_db

router = APIRouter(tags=["species"])


@router.get("/species", response_model=SpeciesBrowsePage)
def browse_species(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    has_sequences: bool | None = Query(None, description="Filter to species with/without COI sequences"),
    has_edges: bool | None = Query(None, description="Filter to species with/without MI edges"),
    is_extinct: bool | None = Query(None, description="Filter by extinct status"),
    clade: int | None = Query(None, description="Filter to descendants of this ott_id"),
    sort: str = Query("name", pattern="^(name|edges)$", description="Sort by name or edge count"),
    db: Session = Depends(get_db),
) -> SpeciesBrowsePage:
    """Browse species with optional filters.

    Supports filtering by sequence availability, MI edge presence,
    extinct status, and clade membership. Paginated with offset/limit.
    """
    # Base filter: only species-rank taxa
    filters = [Taxon.rank == "species"]

    # Filter: extinct status
    if is_extinct is not None:
        filters.append(Taxon.is_extinct == is_extinct)

    # Filter: clade membership via lineage array contains
    if clade is not None:
        filters.append(Taxon.lineage.any(clade))

    # Subqueries for sequence/edge existence
    has_seq_subq = (
        db.query(Sequence.ott_id)
        .filter(Sequence.ott_id == Taxon.ott_id, Sequence.is_canonical.is_(True))
        .correlate(Taxon)
        .exists()
    )

    has_edge_subq = (
        db.query(Edge.src_ott_id)
        .filter(
            or_(
                Edge.src_ott_id == Taxon.ott_id,
                Edge.dst_ott_id == Taxon.ott_id,
            )
        )
        .correlate(Taxon)
        .exists()
    )

    if has_sequences is True:
        filters.append(has_seq_subq)
    elif has_sequences is False:
        filters.append(~has_seq_subq)

    if has_edges is True:
        filters.append(has_edge_subq)
    elif has_edges is False:
        filters.append(~has_edge_subq)

    # Count total matching
    total = (
        db.query(func.count(Taxon.ott_id))
        .filter(*filters)
        .scalar()
    ) or 0

    # Build query for fetching rows
    base = db.query(Taxon).filter(*filters)

    # Sort order
    if sort == "edges":
        # Subquery for edge count per species
        edge_count_sq = (
            db.query(func.count())
            .filter(
                or_(
                    Edge.src_ott_id == Taxon.ott_id,
                    Edge.dst_ott_id == Taxon.ott_id,
                )
            )
            .correlate(Taxon)
            .scalar_subquery()
        )
        base = base.order_by(edge_count_sq.desc(), Taxon.name)
    else:
        base = base.order_by(Taxon.name)

    # Fetch page
    rows = base.offset(offset).limit(limit).all()

    if not rows:
        return SpeciesBrowsePage(items=[], total=total, offset=offset, limit=limit)

    ott_ids = [t.ott_id for t in rows]

    # Batch: images
    images: dict[int, str] = {}
    media_rows = (
        db.query(NodeMedia.ott_id, NodeMedia.image_url)
        .filter(NodeMedia.ott_id.in_(ott_ids))
        .all()
    )
    images = {ott: url for ott, url in media_rows}

    # Batch: which have canonical sequences
    seq_ott_ids: set[int] = set()
    seq_rows = (
        db.query(Sequence.ott_id)
        .filter(Sequence.ott_id.in_(ott_ids), Sequence.is_canonical.is_(True))
        .all()
    )
    seq_ott_ids = {r[0] for r in seq_rows}

    # Batch: edge counts per species
    edge_counts: dict[int, int] = {}
    src_counts = (
        db.query(Edge.src_ott_id, func.count())
        .filter(Edge.src_ott_id.in_(ott_ids))
        .group_by(Edge.src_ott_id)
        .all()
    )
    for ott, cnt in src_counts:
        edge_counts[ott] = edge_counts.get(ott, 0) + cnt
    dst_counts = (
        db.query(Edge.dst_ott_id, func.count())
        .filter(Edge.dst_ott_id.in_(ott_ids))
        .group_by(Edge.dst_ott_id)
        .all()
    )
    for ott, cnt in dst_counts:
        edge_counts[ott] = edge_counts.get(ott, 0) + cnt

    # Batch: family and order names from lineage arrays
    # Collect all ancestor ott_ids from lineages
    all_ancestor_ids: set[int] = set()
    for t in rows:
        if t.lineage:
            all_ancestor_ids.update(t.lineage)

    # Fetch only family/order ancestors in one query
    ancestor_map: dict[int, tuple[str, str]] = {}  # ott_id -> (name, rank)
    if all_ancestor_ids:
        ancestor_rows = (
            db.query(Taxon.ott_id, Taxon.name, Taxon.rank)
            .filter(
                Taxon.ott_id.in_(all_ancestor_ids),
                Taxon.rank.in_(["family", "order"]),
            )
            .all()
        )
        ancestor_map = {ott: (name, rank) for ott, name, rank in ancestor_rows}

    # Build per-species family/order lookup
    species_family: dict[int, str] = {}
    species_order: dict[int, str] = {}
    for t in rows:
        if t.lineage:
            for anc_id in t.lineage:
                info = ancestor_map.get(anc_id)
                if info:
                    if info[1] == "family":
                        species_family[t.ott_id] = info[0]
                    elif info[1] == "order":
                        species_order[t.ott_id] = info[0]

    return SpeciesBrowsePage(
        items=[
            SpeciesSummary(
                ott_id=t.ott_id,
                name=t.name,
                rank=t.rank,
                image_url=images.get(t.ott_id),
                is_extinct=t.is_extinct,
                has_sequence=t.ott_id in seq_ott_ids,
                edge_count=edge_counts.get(t.ott_id, 0),
                family_name=species_family.get(t.ott_id),
                order_name=species_order.get(t.ott_id),
            )
            for t in rows
        ],
        total=total,
        offset=offset,
        limit=limit,
    )
