"""Tests for MI distance computation."""

import math

from evograph.services.mi_distance import (
    distance_from_nmi,
    entropy,
    mi_from_alignment,
)
from evograph.utils.alignment import AlignmentResult


class TestEntropy:
    def test_uniform_binary(self):
        """H of a fair coin = ln(2)."""
        p = {"A": 0.5, "B": 0.5}
        h = entropy(p)
        assert abs(h - math.log(2)) < 0.01

    def test_certain_outcome(self):
        """H of a certain outcome ~ 0."""
        p = {"A": 1.0}
        h = entropy(p)
        assert h < 0.01

    def test_uniform_4(self):
        """H of uniform distribution over 4 bases = ln(4)."""
        p = {"A": 0.25, "C": 0.25, "G": 0.25, "T": 0.25}
        h = entropy(p)
        assert abs(h - math.log(4)) < 0.01


class TestMiFromAlignment:
    def test_identical_sequences(self):
        """Identical sequences should have high MI (NMI close to 1)."""
        seq = "ATCGATCGATCGATCG" * 10  # 160 bases, well above _MIN_COLUMNS
        aln = AlignmentResult(a=seq, b=seq)
        raw_mi, nmi, n = mi_from_alignment(aln)
        assert n == 160
        assert nmi > 0.95
        assert raw_mi > 0

    def test_too_few_columns(self):
        """Fewer than 50 non-gap columns → zero MI."""
        seq = "ATCG" * 10  # 40 bases
        aln = AlignmentResult(a=seq, b=seq)
        raw_mi, nmi, n = mi_from_alignment(aln)
        assert n == 40
        assert nmi == 0.0
        assert raw_mi == 0.0

    def test_gaps_are_excluded(self):
        """Gap columns should be excluded from MI computation."""
        a = "A" * 60 + "-" * 20
        b = "A" * 60 + "T" * 20
        aln = AlignmentResult(a=a, b=b)
        _, _, n = mi_from_alignment(aln)
        assert n == 60  # only non-gap columns counted

    def test_unrelated_sequences_low_mi(self):
        """Sequences with no consistent pattern should have low MI."""
        # Alternating patterns that create independent distributions
        import random
        random.seed(42)
        bases = "ACGT"
        a = "".join(random.choice(bases) for _ in range(200))
        b = "".join(random.choice(bases) for _ in range(200))
        aln = AlignmentResult(a=a, b=b)
        _, nmi, n = mi_from_alignment(aln)
        assert n == 200
        assert nmi < 0.3  # should be low for random sequences

    def test_nmi_clamped_to_unit(self):
        """NMI should always be in [0, 1]."""
        seq = "ATCG" * 50
        aln = AlignmentResult(a=seq, b=seq)
        _, nmi, _ = mi_from_alignment(aln)
        assert 0.0 <= nmi <= 1.0


class TestDistanceFromNmi:
    def test_identical_distance_zero(self):
        assert distance_from_nmi(1.0) == 0.0

    def test_unrelated_distance_one(self):
        assert distance_from_nmi(0.0) == 1.0

    def test_middle(self):
        assert abs(distance_from_nmi(0.5) - 0.5) < 0.001

    def test_clamped(self):
        assert distance_from_nmi(1.5) == 0.0
        assert distance_from_nmi(-0.5) == 1.0
