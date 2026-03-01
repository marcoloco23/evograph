"""Tests for pipeline logic — canonical selection scoring."""

from unittest.mock import MagicMock

from evograph.db.models import Sequence
from evograph.pipeline.select_canonical import _score


def _make_seq(length: int, quality: dict | None = None) -> Sequence:
    """Create a mock Sequence with the fields _score() needs."""
    s = MagicMock(spec=Sequence)
    s.length = length
    s.quality = quality
    return s


class TestScore:
    """Unit tests for the _score function used in canonical selection."""

    def test_score_no_quality(self):
        """Sequence with no quality dict should score as just its length."""
        seq = _make_seq(658)
        assert _score(seq) == 658

    def test_score_none_quality(self):
        """Explicit None quality should score as just length."""
        seq = _make_seq(500, quality=None)
        assert _score(seq) == 500

    def test_score_empty_quality(self):
        """Empty quality dict should score as just length (0 ambig)."""
        seq = _make_seq(600, quality={})
        assert _score(seq) == 600

    def test_score_with_ambig(self):
        """Score should subtract 10 * ambig from length."""
        seq = _make_seq(658, quality={"ambig": 5})
        assert _score(seq) == 658 - 50  # 608

    def test_score_zero_ambig(self):
        """Zero ambig should give same score as no ambig."""
        seq = _make_seq(658, quality={"ambig": 0})
        assert _score(seq) == 658

    def test_score_high_ambig_can_be_negative(self):
        """Very high ambig count can produce a negative score."""
        seq = _make_seq(100, quality={"ambig": 20})
        assert _score(seq) == 100 - 200  # -100

    def test_score_comparison_longer_wins(self):
        """Longer sequence with no ambiguity beats shorter one."""
        long = _make_seq(800)
        short = _make_seq(400)
        assert _score(long) > _score(short)

    def test_score_comparison_ambig_penalized(self):
        """Longer sequence with many ambiguous bases can lose to shorter clean one."""
        long_ambig = _make_seq(700, quality={"ambig": 50})  # 700 - 500 = 200
        short_clean = _make_seq(500)  # 500
        assert _score(short_clean) > _score(long_ambig)

    def test_canonical_selection_picks_best(self):
        """Simulate the max() selection from select_canonical."""
        seqs = [
            _make_seq(400, quality={"ambig": 2}),   # 380
            _make_seq(658, quality={"ambig": 0}),    # 658 (best)
            _make_seq(600, quality={"ambig": 10}),   # 500
        ]
        best = max(seqs, key=lambda s: _score(s))
        assert best.length == 658

    def test_canonical_selection_with_ties(self):
        """When scores are equal, max() returns the first one found."""
        seqs = [
            _make_seq(500),                          # 500
            _make_seq(510, quality={"ambig": 1}),    # 500 (tie)
            _make_seq(400),                          # 400
        ]
        best = max(seqs, key=lambda s: _score(s))
        # Both first and second score 500; max() returns the first
        assert best.length == 500

    def test_quality_non_dict_treated_as_no_quality(self):
        """If quality is not a dict (e.g. a string), ambig defaults to 0."""
        seq = _make_seq(658, quality="invalid")
        # isinstance check fails, so ambig = 0
        assert _score(seq) == 658
