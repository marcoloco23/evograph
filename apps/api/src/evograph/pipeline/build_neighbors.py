"""Build kNN edges using MI distance.

Supports two strategies:
- 'family': Only compare species within the same family (original, fast)
- 'kmer': Use FAISS k-mer index for cross-family candidate selection (more thorough)

Run as: python -m evograph.pipeline.build_neighbors [--strategy family|kmer] [--k 15]
"""

from __future__ import annotations

import argparse
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


def _load_canonical_sequences(session) -> dict[int, Sequence]:
    """Load all canonical COI sequences keyed by ott_id."""
    rows = session.execute(
        select(Sequence).where(
            Sequence.is_canonical.is_(True), Sequence.marker == "COI"
        )
    ).scalars().all()
    return {seq.ott_id: seq for seq in rows}


def _store_edges(session, src_ott: int, neighbors: list[tuple[int, float, float, int]]) -> None:
    """Store kNN edges for a source species."""
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


def _compute_distances(
    src_seq: str, candidate_ids: list[int], canonical_seqs: dict[int, Sequence], src_ott: int
) -> list[tuple[int, float, float, int]]:
    """Compute MI distances between source and candidate sequences."""
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

    return distances


def _build_with_family_index(session, canonical_seqs: dict[int, Sequence], k: int) -> None:
    """Build kNN edges using family-scoped candidate selection."""
    all_taxa = session.execute(select(Taxon)).scalars().all()
    logger.info("Loaded %d taxa", len(all_taxa))

    species_to_family, family_to_species = build_family_index(all_taxa)
    logger.info(
        "Family index: %d species mapped to %d families",
        len(species_to_family),
        len(family_to_species),
    )

    species_ids = sorted(canonical_seqs.keys())
    total = len(species_ids)

    for idx, src_ott in enumerate(species_ids):
        if (idx + 1) % 100 == 0 or idx == 0:
            logger.info("Progress: %d / %d species", idx + 1, total)

        src_seq = canonical_seqs[src_ott].sequence
        family_id = species_to_family.get(src_ott)

        if family_id is None:
            continue

        candidate_ids = family_to_species.get(family_id, [])
        distances = _compute_distances(src_seq, candidate_ids, canonical_seqs, src_ott)

        distances.sort(key=lambda x: x[1])
        _store_edges(session, src_ott, distances[:k])
        session.commit()

    logger.info("Done. Built kNN edges (family strategy) for %d species.", total)


def _build_with_kmer_index(session, canonical_seqs: dict[int, Sequence], k: int) -> None:
    """Build kNN edges using FAISS k-mer index for cross-family candidate selection."""
    from evograph.services.kmer_index import load_index, sequence_to_kmer_vector, query_candidates

    loaded = load_index()
    if loaded is None:
        logger.warning("No FAISS index found. Run build_kmer_index first, or use --strategy family")
        logger.info("Falling back to family strategy...")
        _build_with_family_index(session, canonical_seqs, k)
        return

    index, index_ott_ids = loaded
    logger.info("Loaded FAISS index with %d vectors", index.ntotal)

    # Use more candidates than k to ensure good coverage after alignment
    n_candidates = min(100, index.ntotal)

    species_ids = sorted(canonical_seqs.keys())
    total = len(species_ids)

    for idx, src_ott in enumerate(species_ids):
        if (idx + 1) % 100 == 0 or idx == 0:
            logger.info("Progress: %d / %d species", idx + 1, total)

        src_seq = canonical_seqs[src_ott].sequence
        query_vec = sequence_to_kmer_vector(src_seq)

        # Get candidate OTT IDs from FAISS
        candidates = query_candidates(index, index_ott_ids, query_vec, n_candidates)
        candidate_ids = [ott_id for ott_id, _ in candidates]

        distances = _compute_distances(src_seq, candidate_ids, canonical_seqs, src_ott)

        distances.sort(key=lambda x: x[1])
        _store_edges(session, src_ott, distances[:k])
        session.commit()

    logger.info("Done. Built kNN edges (kmer strategy) for %d species.", total)


def build_neighbors(strategy: str = "family", k: int = K) -> None:
    """Build kNN edges for all species with canonical sequences.

    Args:
        strategy: 'family' for family-scoped, 'kmer' for FAISS k-mer index.
        k: Number of nearest neighbors to keep.
    """
    session = SessionLocal()
    try:
        canonical_seqs = _load_canonical_sequences(session)
        logger.info("Loaded %d canonical sequences", len(canonical_seqs))

        if strategy == "kmer":
            _build_with_kmer_index(session, canonical_seqs, k)
        else:
            _build_with_family_index(session, canonical_seqs, k)

    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build kNN edges using MI distance")
    parser.add_argument(
        "--strategy", choices=["family", "kmer"], default="family",
        help="Candidate selection strategy (default: family)",
    )
    parser.add_argument(
        "--k", type=int, default=K,
        help=f"Number of nearest neighbors (default: {K})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    build_neighbors(strategy=args.strategy, k=args.k)
