"""k-mer frequency vector index for cross-family neighbor candidate selection.

Converts DNA sequences into normalized k-mer frequency vectors and indexes them
with FAISS for fast approximate nearest neighbor search. This enables finding
similar sequences across taxonomic families without exhaustive pairwise alignment.
"""

from __future__ import annotations

import logging
from itertools import product
from pathlib import Path

import faiss
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_K = 6
KMER_DIM = 4 ** DEFAULT_K  # 4096 for k=6

# Default index storage path
DEFAULT_INDEX_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "kmer_index"


def _build_kmer_vocab(k: int = DEFAULT_K) -> dict[str, int]:
    """Build a mapping from k-mer string to index."""
    bases = "ACGT"
    return {"".join(kmer): i for i, kmer in enumerate(product(bases, repeat=k))}


_KMER_VOCAB = _build_kmer_vocab()


def sequence_to_kmer_vector(seq: str, k: int = DEFAULT_K) -> np.ndarray:
    """Convert a DNA sequence to a normalized k-mer frequency vector.

    Args:
        seq: DNA sequence string (ACGT only, no gaps).
        k: k-mer length (default 6 → 4096-dim vector).

    Returns:
        Normalized float32 vector of shape (4^k,).
    """
    vec = np.zeros(KMER_DIM, dtype=np.float32)

    # Clean sequence: uppercase, only ACGT
    seq = seq.upper()
    count = 0
    for i in range(len(seq) - k + 1):
        kmer = seq[i : i + k]
        idx = _KMER_VOCAB.get(kmer)
        if idx is not None:
            vec[idx] += 1
            count += 1

    # Normalize to unit vector (L2)
    if count > 0:
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm

    return vec


def build_faiss_index(
    sequences: dict[int, str], k: int = DEFAULT_K
) -> tuple[faiss.IndexFlatL2, list[int]]:
    """Build a FAISS L2 index from sequences keyed by OTT ID.

    Args:
        sequences: Mapping of ott_id → DNA sequence string.
        k: k-mer length.

    Returns:
        Tuple of (FAISS index, list of ott_ids in index order).
    """
    ott_ids = sorted(sequences.keys())
    n = len(ott_ids)

    logger.info("Building k-mer vectors for %d sequences (k=%d, dim=%d)...", n, k, KMER_DIM)
    vectors = np.zeros((n, KMER_DIM), dtype=np.float32)
    for i, ott_id in enumerate(ott_ids):
        vectors[i] = sequence_to_kmer_vector(sequences[ott_id], k)

    logger.info("Building FAISS IndexFlatL2...")
    index = faiss.IndexFlatL2(KMER_DIM)
    index.add(vectors)
    logger.info("FAISS index built with %d vectors", index.ntotal)

    return index, ott_ids


def query_candidates(
    index: faiss.IndexFlatL2,
    ott_ids: list[int],
    query_vector: np.ndarray,
    n_candidates: int = 100,
) -> list[tuple[int, float]]:
    """Query the FAISS index for nearest candidate OTT IDs.

    Args:
        index: FAISS index.
        ott_ids: OTT IDs in index order.
        query_vector: k-mer frequency vector for the query sequence.
        n_candidates: Number of candidates to return.

    Returns:
        List of (ott_id, l2_distance) tuples sorted by distance.
    """
    k = min(n_candidates, index.ntotal)
    query = query_vector.reshape(1, -1).astype(np.float32)
    distances, indices = index.search(query, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx >= 0:  # FAISS returns -1 for missing results
            results.append((ott_ids[idx], float(dist)))

    return results


def save_index(
    index: faiss.IndexFlatL2,
    ott_ids: list[int],
    directory: Path | str = DEFAULT_INDEX_DIR,
) -> None:
    """Save FAISS index and OTT ID mapping to disk."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    index_path = directory / "kmer.index"
    ids_path = directory / "ott_ids.npy"

    faiss.write_index(index, str(index_path))
    np.save(str(ids_path), np.array(ott_ids, dtype=np.int64))
    logger.info("Saved FAISS index (%d vectors) to %s", index.ntotal, directory)


def load_index(
    directory: Path | str = DEFAULT_INDEX_DIR,
) -> tuple[faiss.IndexFlatL2, list[int]] | None:
    """Load FAISS index and OTT ID mapping from disk.

    Returns None if index files don't exist.
    """
    directory = Path(directory)
    index_path = directory / "kmer.index"
    ids_path = directory / "ott_ids.npy"

    if not index_path.exists() or not ids_path.exists():
        return None

    index = faiss.read_index(str(index_path))
    ott_ids = np.load(str(ids_path)).tolist()
    logger.info("Loaded FAISS index (%d vectors) from %s", index.ntotal, directory)
    return index, ott_ids
