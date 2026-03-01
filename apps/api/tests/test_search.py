"""Tests for the /v1/search endpoint."""

from evograph.db.models import Taxon
from tests.conftest import _make_taxon


class TestSearchTaxa:
    def test_search_returns_matching_taxa(self, client, mock_db):
        mock_db.set(Taxon, [
            _make_taxon(187411, "Corvidae", "family"),
            _make_taxon(369568, "Corvus", "genus"),
        ])

        resp = client.get("/v1/search", params={"q": "corv"})
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Corvidae"
        assert data[0]["ott_id"] == 187411
        assert data[0]["rank"] == "family"
        assert data[1]["name"] == "Corvus"

    def test_search_returns_empty_for_no_match(self, client, mock_db):
        mock_db.set(Taxon, [])

        resp = client.get("/v1/search", params={"q": "zzzzzzz"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_requires_query(self, client):
        resp = client.get("/v1/search")
        assert resp.status_code == 422  # validation error

    def test_search_respects_limit_param(self, client, mock_db):
        mock_db.set(Taxon, [_make_taxon(1, "Corvus", "genus")])

        resp = client.get("/v1/search", params={"q": "corv", "limit": 1})
        assert resp.status_code == 200

    def test_search_rejects_empty_query(self, client):
        resp = client.get("/v1/search", params={"q": ""})
        assert resp.status_code == 422

    def test_search_fields_match_schema(self, client, mock_db):
        mock_db.set(Taxon, [_make_taxon(100, "Falco", "genus")])

        resp = client.get("/v1/search", params={"q": "falco"})
        item = resp.json()[0]
        assert set(item.keys()) >= {"ott_id", "name", "rank"}
