"""Tests for the health check endpoints."""

from fastapi.testclient import TestClient

from evograph.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "scope" in data


def test_readiness_endpoint_exists():
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "scope" in data
    assert "database" in data


def test_readiness_reports_pool_stats():
    resp = client.get("/health/ready")
    data = resp.json()
    db = data["database"]
    assert "connected" in db
    assert "pool_size" in db
    assert "checked_in" in db
    assert "checked_out" in db
    assert "overflow" in db
