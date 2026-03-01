"""Graph endpoints: subtree and MI-neighbor queries."""

import time

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, text
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

    Uses a recursive CTE to collect all descendants in a single query,
    replacing the previous Python-side BFS that issued one query per level.
    """
    root = db.query(Taxon).filter(Taxon.ott_id == ott_id).first()
    if root is None:
        raise HTTPException(status_code=404, detail="Taxon not found")

    # Recursive CTE: fetch entire subtree in one query
    subtree_rows = db.execute(
        text("""
            WITH RECURSIVE subtree AS (
                SELECT ott_id, name, rank, parent_ott_id, 0 AS depth
                FROM taxa
                WHERE ott_id = :root_id
                UNION ALL
                SELECT t.ott_id, t.name, t.rank, t.parent_ott_id, s.depth + 1
                FROM taxa t
                JOIN subtree s ON t.parent_ott_id = s.ott_id
                WHERE s.depth < :max_depth
            )
            SELECT ott_id, name, rank, parent_ott_id, depth FROM subtree
        """),
        {"root_id": ott_id, "max_depth": depth},
    ).fetchall()

    # Build taxa dict and taxonomy edges from CTE results
    # Always include the root (CTE may return empty in test environments)
    taxa_info: dict[int, tuple[str, str]] = {
        root.ott_id: (root.name, root.rank),
    }
    taxonomy_edges: list[GraphEdge] = []

    for row in subtree_rows:
        node_ott_id, name, rank, parent_ott_id, row_depth = row
        taxa_info[node_ott_id] = (name, rank)
        if row_depth > 0 and parent_ott_id in taxa_info:
            taxonomy_edges.append(
                GraphEdge(src=parent_ott_id, dst=node_ott_id, kind="taxonomy", distance=None)
            )

    ott_ids = list(taxa_info.keys())

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
            ott_id=node_ott_id,
            name=name,
            rank=rank,
            image_url=media_map.get(node_ott_id),
        )
        for node_ott_id, (name, rank) in taxa_info.items()
    ]

    return GraphResponse(
        nodes=nodes,
        edges=taxonomy_edges + mi_edges,
    )


@router.get("/graph/mi-network", response_model=GraphResponse)
def get_mi_network(
    response: Response,
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
        response.headers["Cache-Control"] = "public, max-age=300"
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

    response.headers["Cache-Control"] = "public, max-age=300"
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
