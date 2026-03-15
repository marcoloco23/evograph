"""Tests for the /v1/species endpoint."""

from evograph.db.models import Edge, Sequence, Taxon
from tests.conftest import _make_taxon


class TestBrowseSpecies:
    def test_returns_species_list(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
            _make_taxon(893498, "Corvus corone", "species"),
        ])

        resp = client.get("/v1/species")
        assert resp.status_code == 200

        data = resp.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "Corvus corax"
        assert data["items"][0]["ott_id"] == 700118
        assert data["items"][0]["rank"] == "species"

    def test_returns_empty_for_no_species(self, client, mock_db):
        mock_db.set(Taxon, [])

        resp = client.get("/v1/species")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_response_includes_pagination_fields(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])

        resp = client.get("/v1/species", params={"offset": 10, "limit": 25})
        assert resp.status_code == 200
        data = resp.json()
        assert data["offset"] == 10
        assert data["limit"] == 25
        assert "total" in data

    def test_species_includes_has_sequence_field(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])
        mock_db.set(Sequence, [])

        resp = client.get("/v1/species")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "has_sequence" in item
        assert isinstance(item["has_sequence"], bool)

    def test_species_includes_edge_count_field(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])
        mock_db.set(Edge, [])

        resp = client.get("/v1/species")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "edge_count" in item
        assert isinstance(item["edge_count"], int)

    def test_accepts_has_sequences_filter(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])

        resp = client.get("/v1/species", params={"has_sequences": "true"})
        assert resp.status_code == 200

    def test_accepts_has_edges_filter(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])

        resp = client.get("/v1/species", params={"has_edges": "true"})
        assert resp.status_code == 200

    def test_accepts_is_extinct_filter(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])

        resp = client.get("/v1/species", params={"is_extinct": "false"})
        assert resp.status_code == 200

    def test_accepts_sort_param(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])

        resp = client.get("/v1/species", params={"sort": "edges"})
        assert resp.status_code == 200

        resp = client.get("/v1/species", params={"sort": "name"})
        assert resp.status_code == 200

    def test_rejects_invalid_sort_param(self, client, mock_db):
        resp = client.get("/v1/species", params={"sort": "invalid"})
        assert resp.status_code == 422

    def test_limit_validation(self, client, mock_db):
        resp = client.get("/v1/species", params={"limit": 0})
        assert resp.status_code == 422

        resp = client.get("/v1/species", params={"limit": 101})
        assert resp.status_code == 422

    def test_species_image_url_defaults_to_null(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])

        resp = client.get("/v1/species")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "image_url" in item
        assert item["image_url"] is None

    def test_species_fields_match_schema(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])

        resp = client.get("/v1/species")
        data = resp.json()
        assert set(data.keys()) >= {"items", "total", "offset", "limit"}
        item = data["items"][0]
        assert set(item.keys()) >= {
            "ott_id", "name", "rank", "has_sequence", "edge_count",
            "family_name", "order_name",
        }

    def test_species_taxonomy_defaults_to_null(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(700118, "Corvus corax", "species"),
        ])

        resp = client.get("/v1/species")
        item = resp.json()["items"][0]
        # Without lineage data, family/order default to null
        assert item["family_name"] is None
        assert item["order_name"] is None
