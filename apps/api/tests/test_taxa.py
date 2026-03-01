"""Tests for the /v1/taxa/{ott_id} endpoint."""

from evograph.db.models import NodeMedia, Sequence, Taxon
from tests.conftest import _make_media, _make_sequence, _make_taxon


class TestGetTaxon:
    def test_taxon_detail_basic(self, client, mock_db):
        corvidae = _make_taxon(187411, "Corvidae", "family", parent_ott_id=1041547)
        corvus = _make_taxon(369568, "Corvus", "genus", parent_ott_id=187411)
        parent = _make_taxon(1041547, "Passeriformes", "order")

        # First query: get the taxon itself
        # Second query: get children
        # Third+ queries: batch counts, images, canonical check, media, lineage walk
        mock_db.set(Taxon, [corvidae, corvus, parent])
        mock_db.set(Sequence, [])
        mock_db.set(NodeMedia, [])

        resp = client.get("/v1/taxa/187411")
        assert resp.status_code == 200

        data = resp.json()
        assert data["ott_id"] == 187411
        assert data["name"] == "Corvidae"
        assert data["rank"] == "family"

    def test_taxon_not_found(self, client, mock_db):
        mock_db.set(Taxon, [])

        resp = client.get("/v1/taxa/999999")
        assert resp.status_code == 404

    def test_taxon_includes_wikipedia_url(self, client, mock_db):
        taxon = _make_taxon(700118, "Corvus corax", "species")
        mock_db.set(Taxon, [taxon])
        mock_db.set(Sequence, [])
        mock_db.set(NodeMedia, [])

        resp = client.get("/v1/taxa/700118")
        data = resp.json()
        assert data["wikipedia_url"] == "https://en.wikipedia.org/wiki/Corvus_corax"

    def test_taxon_response_fields(self, client, mock_db):
        taxon = _make_taxon(81461, "Aves", "class")
        mock_db.set(Taxon, [taxon])
        mock_db.set(Sequence, [])
        mock_db.set(NodeMedia, [])

        resp = client.get("/v1/taxa/81461")
        data = resp.json()
        expected_keys = {
            "ott_id", "name", "rank", "parent_ott_id", "parent_name",
            "ncbi_tax_id", "children", "total_children",
            "has_canonical_sequence", "image_url", "lineage", "wikipedia_url",
        }
        assert expected_keys <= set(data.keys())


class TestGetChildren:
    def test_children_basic(self, client, mock_db):
        parent = _make_taxon(187411, "Corvidae", "family")
        corvus = _make_taxon(369568, "Corvus", "genus", parent_ott_id=187411)

        mock_db.set(Taxon, [parent, corvus])
        mock_db.set(NodeMedia, [])

        resp = client.get("/v1/taxa/187411/children")
        assert resp.status_code == 200

        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data

    def test_children_not_found(self, client, mock_db):
        mock_db.set(Taxon, [])

        resp = client.get("/v1/taxa/999999/children")
        assert resp.status_code == 404

    def test_children_pagination_params(self, client, mock_db):
        parent = _make_taxon(187411, "Corvidae", "family")
        mock_db.set(Taxon, [parent])
        mock_db.set(NodeMedia, [])

        resp = client.get("/v1/taxa/187411/children", params={"offset": 10, "limit": 50})
        assert resp.status_code == 200
        data = resp.json()
        assert data["offset"] == 10
        assert data["limit"] == 50
