"""Mutual-information-derived distance between aligned DNA sequences."""

from __future__ import annotations

import math
from collections import Counter

from evograph.utils.alignment import AlignmentResult

_ALPHABET = frozenset("ACGTN")
_EPS = 1e-12
_MIN_COLUMNS = 50


def entropy(p: dict[str, float]) -> float:
    """Shannon entropy H(X) = -sum p(x) * log(p(x)) (natural log)."""
    h = 0.0
    for prob in p.values():
        if prob > 0.0:
            h -= prob * math.log(prob + _EPS)
    return h


def mi_from_alignment(aln: AlignmentResult) -> tuple[float, float, int]:
    """Compute mutual information from an alignment.

    Returns
    -------
    raw_mi : float
        Raw mutual information (nats).
    nmi : float
        Normalised MI = MI / min(H(X), H(Y)), in [0, 1].
    num_columns : int
        Number of non-gap columns used.
    """
    assert len(aln.a) == len(aln.b), "Aligned sequences must have equal length."

    # Collect non-gap columns.
    columns: list[tuple[str, str]] = []
    for x, y in zip(aln.a, aln.b):
        if x != "-" and y != "-":
            columns.append((x.upper(), y.upper()))

    n = len(columns)
    if n < _MIN_COLUMNS:
        return 0.0, 0.0, n

    # Joint and marginal counts.
    joint_counts: Counter[tuple[str, str]] = Counter(columns)
    x_counts: Counter[str] = Counter(x for x, _ in columns)
    y_counts: Counter[str] = Counter(y for _, y in columns)

    # Empirical distributions.
    p_x: dict[str, float] = {x: count / n for x, count in x_counts.items()}
    p_y: dict[str, float] = {y: count / n for y, count in y_counts.items()}

    h_x = entropy(p_x)
    h_y = entropy(p_y)

    # MI = sum P(x,y) * log(P(x,y) / (P(x)*P(y)))
    mi = 0.0
    for (x, y), count in joint_counts.items():
        pxy = count / n
        px = x_counts[x] / n
        py = y_counts[y] / n
        mi += pxy * math.log((pxy + _EPS) / (px * py + _EPS))

    min_h = min(h_x, h_y)
    nmi = mi / min_h if min_h > _EPS else 0.0
    # Clamp to [0, 1] to guard against floating-point overshoot.
    nmi = max(0.0, min(1.0, nmi))

    return mi, nmi, n


def distance_from_nmi(nmi: float) -> float:
    """Convert normalised MI to a distance in [0, 1]."""
    return max(0.0, min(1.0, 1.0 - nmi))
