"""Tests for the /v1/graph/* endpoints."""

from evograph.db.models import Edge, NodeMedia, Taxon
from tests.conftest import _make_edge, _make_taxon


class TestSubtreeGraph:
    def test_subtree_returns_graph(self, client, mock_db):
        corvidae = _make_taxon(187411, "Corvidae", "family")
        corvus = _make_taxon(369568, "Corvus", "genus", parent_ott_id=187411)

        mock_db.set(Taxon, [corvidae, corvus])
        mock_db.set(Edge, [])
        mock_db.set(NodeMedia, [])

        resp = client.get("/v1/graph/subtree/187411", params={"depth": 1})
        assert resp.status_code == 200

        data = resp.json()
        assert "nodes" in data
        assert "edges" in data

    def test_subtree_not_found(self, client, mock_db):
        mock_db.set(Taxon, [])

        resp = client.get("/v1/graph/subtree/999999")
        assert resp.status_code == 404

    def test_subtree_depth_validation(self, client, mock_db):
        taxon = _make_taxon(187411, "Corvidae", "family")
        mock_db.set(Taxon, [taxon])
        mock_db.set(Edge, [])
        mock_db.set(NodeMedia, [])

        # Depth 0 should fail validation (min is 1)
        resp = client.get("/v1/graph/subtree/187411", params={"depth": 0})
        assert resp.status_code == 422

        # Depth 6 should fail validation (max is 5)
        resp = client.get("/v1/graph/subtree/187411", params={"depth": 6})
        assert resp.status_code == 422

    def test_subtree_graph_schema(self, client, mock_db):
        taxon = _make_taxon(187411, "Corvidae", "family")
        mock_db.set(Taxon, [taxon])
        mock_db.set(Edge, [])
        mock_db.set(NodeMedia, [])

        resp = client.get("/v1/graph/subtree/187411")
        data = resp.json()

        # Root node must be present
        assert any(n["ott_id"] == 187411 for n in data["nodes"])
        for node in data["nodes"]:
            assert "ott_id" in node
            assert "name" in node
            assert "rank" in node


class TestMiNetwork:
    def test_mi_network_empty(self, client, mock_db):
        mock_db.set(Edge, [])

        resp = client.get("/v1/graph/mi-network")
        assert resp.status_code == 200

        data = resp.json()
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_mi_network_returns_edges_and_nodes(self, client, mock_db):
        edge = _make_edge(700118, 893498, distance=0.15, mi_norm=0.85)
        corax = _make_taxon(700118, "Corvus corax", "species", parent_ott_id=369568)
        corone = _make_taxon(893498, "Corvus corone", "species", parent_ott_id=369568)

        mock_db.set(Edge, [edge])
        mock_db.set(Taxon, [corax, corone])
        mock_db.set(NodeMedia, [])

        resp = client.get("/v1/graph/mi-network")
        assert resp.status_code == 200

        data = resp.json()
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 1

    def test_mi_network_edge_schema(self, client, mock_db):
        edge = _make_edge(700118, 893498)
        corax = _make_taxon(700118, "Corvus corax", "species")
        corone = _make_taxon(893498, "Corvus corone", "species")

        mock_db.set(Edge, [edge])
        mock_db.set(Taxon, [corax, corone])
        mock_db.set(NodeMedia, [])

        resp = client.get("/v1/graph/mi-network")
        mi_edges = [e for e in resp.json()["edges"] if e["kind"] == "mi"]
        assert len(mi_edges) >= 1
        for e in mi_edges:
            assert "src" in e
            assert "dst" in e
            assert "distance" in e


class TestNeighbors:
    def test_neighbors_returns_sorted(self, client, mock_db):
        taxon = _make_taxon(700118, "Corvus corax", "species")
        corone = _make_taxon(893498, "Corvus corone", "species")
        edge = _make_edge(700118, 893498, distance=0.15, mi_norm=0.85)

        mock_db.set(Taxon, [taxon])
        mock_db.set((Edge, Taxon), [(edge, corone)])

        resp = client.get("/v1/graph/neighbors/700118")
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) == 1
        assert data[0]["ott_id"] == 893498
        assert data[0]["distance"] == 0.15
        assert data[0]["mi_norm"] == 0.85

    def test_neighbors_not_found(self, client, mock_db):
        mock_db.set(Taxon, [])

        resp = client.get("/v1/graph/neighbors/999999")
        assert resp.status_code == 404

    def test_neighbors_k_validation(self, client, mock_db):
        taxon = _make_taxon(700118, "Corvus corax", "species")
        mock_db.set(Taxon, [taxon])
        mock_db.set((Edge, Taxon), [])

        # k=0 should fail (min is 1)
        resp = client.get("/v1/graph/neighbors/700118", params={"k": 0})
        assert resp.status_code == 422

        # k=51 should fail (max is 50)
        resp = client.get("/v1/graph/neighbors/700118", params={"k": 51})
        assert resp.status_code == 422

    def test_neighbors_empty_result(self, client, mock_db):
        taxon = _make_taxon(700118, "Corvus corax", "species")
        mock_db.set(Taxon, [taxon])
        mock_db.set((Edge, Taxon), [])

        resp = client.get("/v1/graph/neighbors/700118")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_neighbor_schema(self, client, mock_db):
        taxon = _make_taxon(700118, "Corvus corax", "species")
        corone = _make_taxon(893498, "Corvus corone", "species")
        edge = _make_edge(700118, 893498, distance=0.2, mi_norm=0.8)

        mock_db.set(Taxon, [taxon])
        mock_db.set((Edge, Taxon), [(edge, corone)])

        resp = client.get("/v1/graph/neighbors/700118")
        item = resp.json()[0]
        assert set(item.keys()) == {"ott_id", "name", "rank", "distance", "mi_norm"}
