"""Tests for the validation pipeline."""

from unittest.mock import MagicMock

from evograph.pipeline.validate import (
    OutlierRecord,
    ValidationReport,
    _walk_to_rank,
    compute_validation_report,
)


class TestWalkToRank:
    """Tests for _walk_to_rank helper."""

    def test_finds_genus(self):
        species = MagicMock(ott_id=1, rank="species", parent_ott_id=2)
        genus = MagicMock(ott_id=2, rank="genus", parent_ott_id=3)
        family = MagicMock(ott_id=3, rank="family", parent_ott_id=None)
        taxa = {1: species, 2: genus, 3: family}

        assert _walk_to_rank(1, "genus", taxa) == 2

    def test_finds_family(self):
        species = MagicMock(ott_id=1, rank="species", parent_ott_id=2)
        genus = MagicMock(ott_id=2, rank="genus", parent_ott_id=3)
        family = MagicMock(ott_id=3, rank="family", parent_ott_id=None)
        taxa = {1: species, 2: genus, 3: family}

        assert _walk_to_rank(1, "family", taxa) == 3

    def test_returns_none_when_rank_not_found(self):
        species = MagicMock(ott_id=1, rank="species", parent_ott_id=None)
        taxa = {1: species}

        assert _walk_to_rank(1, "genus", taxa) is None

    def test_returns_none_for_missing_taxon(self):
        assert _walk_to_rank(999, "genus", {}) is None

    def test_handles_circular_reference(self):
        """Should not infinite loop on circular parent references."""
        a = MagicMock(ott_id=1, rank="species", parent_ott_id=2)
        b = MagicMock(ott_id=2, rank="species", parent_ott_id=1)
        taxa = {1: a, 2: b}

        assert _walk_to_rank(1, "genus", taxa) is None

    def test_returns_self_if_already_at_rank(self):
        genus = MagicMock(ott_id=5, rank="genus", parent_ott_id=10)
        taxa = {5: genus}

        assert _walk_to_rank(5, "genus", taxa) == 5


class TestValidationReport:
    """Tests for ValidationReport dataclass."""

    def test_to_dict_structure(self):
        report = ValidationReport(
            total_edges=100,
            same_genus_count=60,
            same_family_count=85,
            same_genus_pct=60.0,
            same_family_pct=85.0,
            distance_min=0.01,
            distance_max=0.95,
            distance_mean=0.45,
            distance_median=0.42,
            distance_stdev=0.15,
            outliers=[
                OutlierRecord(
                    src_ott_id=1, src_name="A", dst_ott_id=2, dst_name="B",
                    distance=0.03, reason="cross_family_close",
                ),
                OutlierRecord(
                    src_ott_id=3, src_name="C", dst_ott_id=4, dst_name="D",
                    distance=0.85, reason="within_genus_distant",
                ),
            ],
        )
        d = report.to_dict()

        assert d["total_edges"] == 100
        assert d["taxonomy_coherence"]["same_genus"] == 60
        assert d["taxonomy_coherence"]["same_family_pct"] == 85.0
        assert d["distance_distribution"]["mean"] == 0.45
        assert len(d["outliers"]["cross_family_close"]) == 1
        assert len(d["outliers"]["within_genus_distant"]) == 1
        assert d["outliers"]["cross_family_close"][0]["src_name"] == "A"

    def test_to_dict_no_stdev_with_single_edge(self):
        report = ValidationReport(
            total_edges=1,
            distance_min=0.5,
            distance_max=0.5,
            distance_mean=0.5,
            distance_median=0.5,
            distance_stdev=None,
        )
        d = report.to_dict()
        assert d["distance_distribution"]["stdev"] is None


class TestComputeValidationReport:
    """Tests for compute_validation_report."""

    def test_returns_none_when_no_edges(self):
        mock_session = MagicMock()
        # First call returns taxa, second returns edges
        taxa_result = MagicMock()
        taxa_result.scalars.return_value.all.return_value = []
        edges_result = MagicMock()
        edges_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [taxa_result, edges_result]

        result = compute_validation_report(mock_session)
        assert result is None

    def test_counts_same_genus_edges(self):
        # Build taxa: two species in same genus
        species_a = MagicMock(ott_id=1, rank="species", parent_ott_id=10, name="Species A")
        species_b = MagicMock(ott_id=2, rank="species", parent_ott_id=10, name="Species B")
        genus = MagicMock(ott_id=10, rank="genus", parent_ott_id=100, name="Genus")
        family = MagicMock(ott_id=100, rank="family", parent_ott_id=None, name="Family")

        edge = MagicMock(src_ott_id=1, dst_ott_id=2, distance=0.3)

        mock_session = MagicMock()
        taxa_result = MagicMock()
        taxa_result.scalars.return_value.all.return_value = [species_a, species_b, genus, family]
        edges_result = MagicMock()
        edges_result.scalars.return_value.all.return_value = [edge]
        mock_session.execute.side_effect = [taxa_result, edges_result]

        report = compute_validation_report(mock_session)
        assert report is not None
        assert report.same_genus_count == 1
        assert report.same_family_count == 1
        assert report.total_edges == 1

    def test_detects_cross_family_outlier(self):
        # Two species in different families with very low distance
        sp_a = MagicMock(ott_id=1, rank="species", parent_ott_id=10, name="Sp A")
        sp_b = MagicMock(ott_id=2, rank="species", parent_ott_id=20, name="Sp B")
        genus_a = MagicMock(ott_id=10, rank="genus", parent_ott_id=100, name="GenA")
        genus_b = MagicMock(ott_id=20, rank="genus", parent_ott_id=200, name="GenB")
        fam_a = MagicMock(ott_id=100, rank="family", parent_ott_id=None, name="FamA")
        fam_b = MagicMock(ott_id=200, rank="family", parent_ott_id=None, name="FamB")

        edge = MagicMock(src_ott_id=1, dst_ott_id=2, distance=0.02)

        mock_session = MagicMock()
        taxa_result = MagicMock()
        taxa_result.scalars.return_value.all.return_value = [
            sp_a, sp_b, genus_a, genus_b, fam_a, fam_b,
        ]
        edges_result = MagicMock()
        edges_result.scalars.return_value.all.return_value = [edge]
        mock_session.execute.side_effect = [taxa_result, edges_result]

        report = compute_validation_report(mock_session)
        assert report is not None
        cross_family = [o for o in report.outliers if o.reason == "cross_family_close"]
        assert len(cross_family) == 1
        assert cross_family[0].distance == 0.02

    def test_detects_within_genus_distant_outlier(self):
        # Two species in same genus with very high distance
        sp_a = MagicMock(ott_id=1, rank="species", parent_ott_id=10, name="Sp A")
        sp_b = MagicMock(ott_id=2, rank="species", parent_ott_id=10, name="Sp B")
        genus = MagicMock(ott_id=10, rank="genus", parent_ott_id=100, name="Genus")
        family = MagicMock(ott_id=100, rank="family", parent_ott_id=None, name="Fam")

        edge = MagicMock(src_ott_id=1, dst_ott_id=2, distance=0.9)

        mock_session = MagicMock()
        taxa_result = MagicMock()
        taxa_result.scalars.return_value.all.return_value = [sp_a, sp_b, genus, family]
        edges_result = MagicMock()
        edges_result.scalars.return_value.all.return_value = [edge]
        mock_session.execute.side_effect = [taxa_result, edges_result]

        report = compute_validation_report(mock_session)
        assert report is not None
        within_genus = [o for o in report.outliers if o.reason == "within_genus_distant"]
        assert len(within_genus) == 1
        assert within_genus[0].distance == 0.9
