"""Tests for the /v1/taxa/{ott_id}/sequences endpoint."""

from evograph.db.models import Sequence, Taxon
from tests.conftest import _make_sequence, _make_taxon


class TestGetSequences:
    def test_sequences_returns_list(self, client, mock_db):
        taxon = _make_taxon(700118, "Corvus corax", "species")
        seq = _make_sequence(700118, accession="NC_001", length=658, is_canonical=True)

        mock_db.set(Taxon, [taxon])
        mock_db.set(Sequence, [seq])

        resp = client.get("/v1/taxa/700118/sequences")
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) == 1
        assert data[0]["ott_id"] == 700118
        assert data[0]["marker"] == "COI"
        assert data[0]["source"] == "NCBI"
        assert data[0]["accession"] == "NC_001"
        assert data[0]["length"] == 658
        assert data[0]["is_canonical"] is True

    def test_sequences_taxon_not_found(self, client, mock_db):
        mock_db.set(Taxon, [])

        resp = client.get("/v1/taxa/999999/sequences")
        assert resp.status_code == 404

    def test_sequences_empty(self, client, mock_db):
        taxon = _make_taxon(700118, "Corvus corax", "species")
        mock_db.set(Taxon, [taxon])
        mock_db.set(Sequence, [])

        resp = client.get("/v1/taxa/700118/sequences")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_sequence_schema_fields(self, client, mock_db):
        taxon = _make_taxon(700118, "Corvus corax", "species")
        seq = _make_sequence(700118)
        mock_db.set(Taxon, [taxon])
        mock_db.set(Sequence, [seq])

        resp = client.get("/v1/taxa/700118/sequences")
        item = resp.json()[0]
        expected_keys = {"id", "ott_id", "marker", "source", "accession", "sequence", "length", "is_canonical", "retrieved_at"}
        assert expected_keys == set(item.keys())
