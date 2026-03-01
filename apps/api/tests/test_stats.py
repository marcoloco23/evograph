"""Tests for the stats endpoint."""


def test_stats_returns_structure(client):
    """Stats endpoint returns expected top-level keys."""
    resp = client.get("/v1/stats")
    assert resp.status_code == 200
    data = resp.json()

    assert "taxa" in data
    assert "sequences" in data
    assert "edges" in data
    assert "total" in data["taxa"]
    assert "by_rank" in data["taxa"]
    assert "total" in data["sequences"]
    assert "total" in data["edges"]


def test_stats_empty_database(client):
    """Stats endpoint handles empty database gracefully."""
    resp = client.get("/v1/stats")
    assert resp.status_code == 200
    data = resp.json()

    assert data["taxa"]["total"] == 0
    assert data["sequences"]["total"] == 0
    assert data["edges"]["total"] == 0
    assert data["edges"]["distance"] is None
