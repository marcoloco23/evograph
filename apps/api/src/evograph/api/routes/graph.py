"""Graph endpoints: subtree and MI-neighbor queries."""

import time
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session

from evograph.api.schemas.graph import GraphEdge, GraphResponse, NeighborOut, Node
from evograph.db.models import Edge, NodeMedia, Taxon
from evograph.db.session import get_db

router = APIRouter(tags=["graph"])

# ── In-memory cache for MI network (expensive query) ──────
_mi_network_cache: GraphResponse | None = None
_mi_network_cache_time: float = 0.0
_MI_NETWORK_TTL: float = 300.0  # 5 minutes


@router.get("/graph/subtree/{ott_id}", response_model=GraphResponse)
def get_subtree_graph(
    ott_id: int,
    depth: int = Query(3, ge=1, le=5),
    db: Session = Depends(get_db),
) -> GraphResponse:
    """Get a graph containing the taxonomy subtree + MI edges among those nodes.

    Walk down from ott_id collecting descendants up to `depth` levels.
    Include taxonomy edges (parent->child) and MI edges between nodes in the set.
    """
    root = db.query(Taxon).filter(Taxon.ott_id == ott_id).first()
    if root is None:
        raise HTTPException(status_code=404, detail="Taxon not found")

    # BFS to collect descendants up to `depth` levels
    collected: dict[int, Taxon] = {root.ott_id: root}
    taxonomy_edges: list[GraphEdge] = []
    queue: deque[tuple[int, int]] = deque([(root.ott_id, 0)])

    while queue:
        current_id, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        children = (
            db.query(Taxon).filter(Taxon.parent_ott_id == current_id).all()
        )
        for child in children:
            if child.ott_id not in collected:
                collected[child.ott_id] = child
                taxonomy_edges.append(
                    GraphEdge(
                        src=current_id,
                        dst=child.ott_id,
                        kind="taxonomy",
                        distance=None,
                    )
                )
                queue.append((child.ott_id, current_depth + 1))

    ott_ids = list(collected.keys())

    # Fetch image URLs for all collected nodes
    media_rows = (
        db.query(NodeMedia).filter(NodeMedia.ott_id.in_(ott_ids)).all()
    )
    media_map = {m.ott_id: m.image_url for m in media_rows}

    # Query MI edges where both src and dst are in the collected set
    mi_edges: list[GraphEdge] = []
    if len(ott_ids) > 1:
        edge_rows = (
            db.query(Edge)
            .filter(
                and_(
                    Edge.src_ott_id.in_(ott_ids),
                    Edge.dst_ott_id.in_(ott_ids),
                )
            )
            .all()
        )
        for e in edge_rows:
            mi_edges.append(
                GraphEdge(
                    src=e.src_ott_id,
                    dst=e.dst_ott_id,
                    kind="mi",
                    distance=e.distance,
                )
            )

    nodes = [
        Node(
            ott_id=t.ott_id,
            name=t.name,
            rank=t.rank,
            image_url=media_map.get(t.ott_id),
        )
        for t in collected.values()
    ]

    return GraphResponse(
        nodes=nodes,
        edges=taxonomy_edges + mi_edges,
    )


@router.get("/graph/mi-network", response_model=GraphResponse)
def get_mi_network(
    db: Session = Depends(get_db),
) -> GraphResponse:
    """Get the full MI similarity network: all species with MI edges.

    Returns all taxa that have at least one MI edge, plus all MI edges
    between them (deduplicated to undirected). Includes taxonomy edges
    connecting species to their parent genus.

    Results are cached in-memory for 5 minutes.
    """
    global _mi_network_cache, _mi_network_cache_time
    now = time.monotonic()
    if _mi_network_cache is not None and (now - _mi_network_cache_time) < _MI_NETWORK_TTL:
        return _mi_network_cache

    # Get all MI edges
    all_edges = db.query(Edge).all()
    if not all_edges:
        return GraphResponse(nodes=[], edges=[])

    # Collect all involved OTT IDs
    ott_ids: set[int] = set()
    for e in all_edges:
        ott_ids.add(e.src_ott_id)
        ott_ids.add(e.dst_ott_id)

    # Fetch taxa in one query
    taxa = db.query(Taxon).filter(Taxon.ott_id.in_(ott_ids)).all()
    taxa_map = {t.ott_id: t for t in taxa}

    # Fetch media in one query
    media_rows = db.query(NodeMedia).filter(NodeMedia.ott_id.in_(ott_ids)).all()
    media_map = {m.ott_id: m.image_url for m in media_rows}

    # Build MI edges — deduplicate to undirected (keep the one with lower distance
    # when both A->B and B->A exist, otherwise keep the single direction)
    seen_pairs: dict[tuple[int, int], float] = {}
    for e in all_edges:
        pair = (min(e.src_ott_id, e.dst_ott_id), max(e.src_ott_id, e.dst_ott_id))
        if pair not in seen_pairs or e.distance < seen_pairs[pair]:
            seen_pairs[pair] = e.distance

    mi_edges = [
        GraphEdge(src=a, dst=b, kind="mi", distance=dist)
        for (a, b), dist in seen_pairs.items()
    ]

    # Add taxonomy edges: connect species to their parent genus/family
    # Batch-fetch all parent taxa in one query (no N+1)
    parent_ids = {
        t.parent_ott_id
        for t in taxa_map.values()
        if t.parent_ott_id and t.parent_ott_id not in taxa_map
    }
    if parent_ids:
        parents = db.query(Taxon).filter(Taxon.ott_id.in_(parent_ids)).all()
        for p in parents:
            taxa_map[p.ott_id] = p

    taxonomy_edges = []
    for ott_id in ott_ids:
        t = taxa_map.get(ott_id)
        if t and t.parent_ott_id and t.parent_ott_id in taxa_map:
            taxonomy_edges.append(
                GraphEdge(src=t.parent_ott_id, dst=ott_id, kind="taxonomy", distance=None)
            )

    nodes = [
        Node(
            ott_id=t.ott_id,
            name=t.name,
            rank=t.rank,
            image_url=media_map.get(t.ott_id),
        )
        for t in taxa_map.values()
    ]

    result = GraphResponse(nodes=nodes, edges=mi_edges + taxonomy_edges)
    _mi_network_cache = result
    _mi_network_cache_time = time.monotonic()
    return result


@router.get("/graph/neighbors/{ott_id}", response_model=list[NeighborOut])
def get_neighbors(
    ott_id: int,
    k: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[NeighborOut]:
    """Get k nearest MI-neighbors for a taxon.

    Query Edge table where src_ott_id = ott_id, order by distance, limit k.
    Join with Taxon to get name/rank.
    """
    taxon = db.query(Taxon).filter(Taxon.ott_id == ott_id).first()
    if taxon is None:
        raise HTTPException(status_code=404, detail="Taxon not found")

    rows = (
        db.query(Edge, Taxon)
        .join(Taxon, Edge.dst_ott_id == Taxon.ott_id)
        .filter(Edge.src_ott_id == ott_id)
        .order_by(Edge.distance)
        .limit(k)
        .all()
    )

    return [
        NeighborOut(
            ott_id=t.ott_id,
            name=t.name,
            rank=t.rank,
            distance=e.distance,
            mi_norm=e.mi_norm,
        )
        for e, t in rows
    ]
