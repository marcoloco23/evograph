"""Build kNN edges using MI distance.

Run as: python -m evograph.pipeline.build_neighbors
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from evograph.db.models import Edge, Sequence, Taxon
from evograph.db.session import SessionLocal
from evograph.services.mi_distance import distance_from_nmi, mi_from_alignment
from evograph.services.neighbor_index import build_family_index
from evograph.utils.alignment import global_align

logger = logging.getLogger(__name__)

K = 15  # number of nearest neighbors to keep


def build_neighbors() -> None:
    """Build kNN edges for all species with canonical sequences."""
    session = SessionLocal()
    try:
        # Load all taxa for family index
        all_taxa = session.execute(select(Taxon)).scalars().all()
        logger.info("Loaded %d taxa", len(all_taxa))

        species_to_family, family_to_species = build_family_index(all_taxa)
        logger.info(
            "Family index: %d species mapped to %d families",
            len(species_to_family),
            len(family_to_species),
        )

        # Load all canonical sequences, keyed by ott_id
        canonical_seqs: dict[int, Sequence] = {}
        rows = session.execute(
            select(Sequence).where(
                Sequence.is_canonical.is_(True), Sequence.marker == "COI"
            )
        ).scalars().all()
        for seq in rows:
            canonical_seqs[seq.ott_id] = seq
        logger.info("Loaded %d canonical sequences", len(canonical_seqs))

        species_ids = sorted(canonical_seqs.keys())
        total = len(species_ids)

        for idx, src_ott in enumerate(species_ids):
            if (idx + 1) % 100 == 0 or idx == 0:
                logger.info("Progress: %d / %d species", idx + 1, total)

            src_seq = canonical_seqs[src_ott].sequence
            family_id = species_to_family.get(src_ott)

            # Get candidates from same family
            if family_id is not None:
                candidate_ids = family_to_species.get(family_id, [])
            else:
                # No family found - skip or use all (skip for efficiency)
                continue

            # Compute distances to all candidates that have canonical sequences
            distances: list[tuple[int, float, float, int]] = []
            for dst_ott in candidate_ids:
                if dst_ott == src_ott:
                    continue
                if dst_ott not in canonical_seqs:
                    continue

                dst_seq = canonical_seqs[dst_ott].sequence
                aln = global_align(src_seq, dst_seq)
                _mi, nmi, n_cols = mi_from_alignment(aln)
                dist = distance_from_nmi(nmi)
                distances.append((dst_ott, dist, nmi, n_cols))

            # Keep top K nearest
            distances.sort(key=lambda x: x[1])
            neighbors = distances[:K]

            # Store edges
            for dst_ott, dist, nmi, n_cols in neighbors:
                stmt = pg_insert(Edge).values(
                    src_ott_id=src_ott,
                    dst_ott_id=dst_ott,
                    marker="COI",
                    distance=dist,
                    mi_norm=nmi,
                    align_len=n_cols,
                ).on_conflict_do_update(
                    index_elements=[Edge.src_ott_id, Edge.dst_ott_id, Edge.marker],
                    set_={
                        "distance": dist,
                        "mi_norm": nmi,
                        "align_len": n_cols,
                    },
                )
                session.execute(stmt)

            session.commit()

        logger.info("Done. Built kNN edges for %d species.", total)

    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    build_neighbors()
