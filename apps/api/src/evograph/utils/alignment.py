"""Global sequence alignment using the parasail library (Needleman-Wunsch)."""

from __future__ import annotations

from dataclasses import dataclass

import parasail


@dataclass(frozen=True)
class AlignmentResult:
    """Pairwise alignment with gap characters."""

    a: str  # aligned sequence A with '-' gaps
    b: str  # aligned sequence B with '-' gaps


def global_align(a: str, b: str) -> AlignmentResult:
    """Global alignment using parasail (Needleman-Wunsch).

    Scoring: match=2, mismatch=-1, gap_open=3, gap_extend=1.
    Returns aligned strings with '-' for gaps.
    """
    a = a.upper()
    b = b.upper()

    matrix = parasail.matrix_create("ACGTN", 2, -1)
    result = parasail.nw_trace_striped_16(a, b, 3, 1, matrix)
    tb = result.traceback

    return AlignmentResult(a=tb.query, b=tb.ref)
