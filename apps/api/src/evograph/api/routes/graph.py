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
                    mi_norm=e.mi_norm,
                    align_len=e.align_len,
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
    limit: int = Query(5000, ge=100, le=50000, description="Max edges to return (closest first)"),
    db: Session = Depends(get_db),
) -> GraphResponse:
    """Get the MI similarity network: species connected by MI edges.

    Returns up to `limit` edges (sorted by distance, closest first),
    deduplicated to undirected. Includes taxonomy edges connecting
    species to their parent genus.

    Results are cached in-memory for 5 minutes.
    """
    global _mi_network_cache, _mi_network_cache_time
    now = time.monotonic()
    cache_key = f"mi_network_{limit}"
    if (
        _mi_network_cache is not None
        and (now - _mi_network_cache_time) < _MI_NETWORK_TTL
        and getattr(_mi_network_cache, "_cache_key", None) == cache_key
    ):
        response.headers["Cache-Control"] = "public, max-age=300"
        return _mi_network_cache

    # Use raw SQL with deduplication and limit for efficiency.
    # Deduplicate directed edges to undirected by keeping the pair with
    # smaller src_ott_id first, taking the minimum distance.
    rows = db.execute(
        text("""
            SELECT DISTINCT ON (LEAST(src_ott_id, dst_ott_id), GREATEST(src_ott_id, dst_ott_id))
                LEAST(src_ott_id, dst_ott_id) AS src,
                GREATEST(src_ott_id, dst_ott_id) AS dst,
                distance, mi_norm, align_len
            FROM edges
            ORDER BY LEAST(src_ott_id, dst_ott_id), GREATEST(src_ott_id, dst_ott_id), distance
        """),
    ).fetchall()

    # Sort by distance and take top N
    rows = sorted(rows, key=lambda r: r.distance)[:limit]

    if not rows:
        return GraphResponse(nodes=[], edges=[])

    # Collect all involved OTT IDs
    ott_ids: set[int] = set()
    for r in rows:
        ott_ids.add(r.src)
        ott_ids.add(r.dst)

    # Fetch taxa in one query
    taxa = db.query(Taxon).filter(Taxon.ott_id.in_(ott_ids)).all()
    taxa_map = {t.ott_id: t for t in taxa}

    # Fetch media in one query
    media_rows = db.query(NodeMedia).filter(NodeMedia.ott_id.in_(ott_ids)).all()
    media_map = {m.ott_id: m.image_url for m in media_rows}

    mi_edges = [
        GraphEdge(src=r.src, dst=r.dst, kind="mi", distance=r.distance,
                  mi_norm=r.mi_norm, align_len=r.align_len)
        for r in rows
    ]

    # Add taxonomy edges: connect species to their parent genus/family
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
    result._cache_key = cache_key  # type: ignore[attr-defined]
    _mi_network_cache = result
    _mi_network_cache_time = time.monotonic()

    response.headers["Cache-Control"] = "public, max-age=300"
    return result


def _find_shared_rank(
    src_lineage: list[int] | None,
    dst_lineage: list[int] | None,
    rank_lookup: dict[int, str],
) -> str | None:
    """Find the deepest shared taxonomic rank between two taxa.

    Lineage arrays run from root -> parent (not including self).
    Walk dst lineage from deepest to shallowest to find the first common ancestor.
    """
    if not src_lineage or not dst_lineage:
        return None

    src_set = set(src_lineage)
    for ott_id in reversed(dst_lineage):
        if ott_id in src_set:
            return rank_lookup.get(ott_id)

    return None


@router.get("/graph/neighbors/{ott_id}", response_model=list[NeighborOut])
def get_neighbors(
    ott_id: int,
    k: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[NeighborOut]:
    """Get k nearest MI-neighbors for a taxon.

    Query Edge table where src_ott_id = ott_id, order by distance, limit k.
    Join with Taxon to get name/rank. Computes shared taxonomic rank
    using lineage arrays to show taxonomy-vs-similarity coherence.
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

    # Collect all lineage ott_ids to batch-lookup ranks
    all_lineage_ids: set[int] = set()
    src_lineage = taxon.lineage or []
    all_lineage_ids.update(src_lineage)
    for _e, t in rows:
        if t.lineage:
            all_lineage_ids.update(t.lineage)

    # Batch-fetch ranks for all lineage ancestors
    rank_lookup: dict[int, str] = {}
    if all_lineage_ids:
        ancestor_rows = (
            db.query(Taxon.ott_id, Taxon.rank)
            .filter(Taxon.ott_id.in_(all_lineage_ids))
            .all()
        )
        rank_lookup = {ott: rank for ott, rank in ancestor_rows}

    return [
        NeighborOut(
            ott_id=t.ott_id,
            name=t.name,
            rank=t.rank,
            distance=e.distance,
            mi_norm=e.mi_norm,
            align_len=e.align_len,
            shared_rank=_find_shared_rank(src_lineage, t.lineage, rank_lookup),
        )
        for e, t in rows
    ]
