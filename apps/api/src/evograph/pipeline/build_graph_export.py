"""Export graph data as JSON for the frontend.

Writes:
  - data/processed/graph/nodes.json
  - data/processed/graph/edges.json

Run as: python -m evograph.pipeline.build_graph_export
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select

from evograph.db.models import Edge, Sequence, Taxon
from evograph.db.session import SessionLocal

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/processed/graph")


def export_graph() -> None:
    """Export nodes and edges as JSON."""
    session = SessionLocal()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Find all ott_ids that have a canonical sequence
        canonical_ott_ids = set(
            session.execute(
                select(Sequence.ott_id).where(
                    Sequence.is_canonical.is_(True), Sequence.marker == "COI"
                )
            )
            .scalars()
            .all()
        )
        logger.info("Found %d taxa with canonical sequences", len(canonical_ott_ids))

        # Query taxa for those ott_ids
        taxa = (
            session.execute(
                select(Taxon).where(Taxon.ott_id.in_(canonical_ott_ids))
            )
            .scalars()
            .all()
        )

        nodes = [
            {
                "ott_id": t.ott_id,
                "name": t.name,
                "rank": t.rank,
                "parent_ott_id": t.parent_ott_id,
            }
            for t in taxa
        ]

        # Query all edges
        edges_orm = session.execute(select(Edge)).scalars().all()
        edges = [
            {
                "src_ott_id": e.src_ott_id,
                "dst_ott_id": e.dst_ott_id,
                "marker": e.marker,
                "distance": e.distance,
                "mi_norm": e.mi_norm,
                "align_len": e.align_len,
            }
            for e in edges_orm
        ]

        # Write JSON files
        nodes_path = OUTPUT_DIR / "nodes.json"
        edges_path = OUTPUT_DIR / "edges.json"

        nodes_path.write_text(
            json.dumps(nodes, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        edges_path.write_text(
            json.dumps(edges, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        logger.info("Exported %d nodes to %s", len(nodes), nodes_path)
        logger.info("Exported %d edges to %s", len(edges), edges_path)

    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    export_graph()
