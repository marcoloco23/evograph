"""Tests for request logging middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from evograph.middleware.request_logging import RequestLoggingMiddleware


def test_request_id_header():
    """Response includes X-Request-ID header."""
    test_app = FastAPI()
    test_app.add_middleware(RequestLoggingMiddleware)

    @test_app.get("/test")
    def test_endpoint():
        return {"ok": True}

    with TestClient(test_app) as client:
        resp = client.get("/test")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) == 8


def test_request_id_unique():
    """Each request gets a unique ID."""
    test_app = FastAPI()
    test_app.add_middleware(RequestLoggingMiddleware)

    @test_app.get("/test")
    def test_endpoint():
        return {"ok": True}

    with TestClient(test_app) as client:
        ids = set()
        for _ in range(5):
            resp = client.get("/test")
            ids.add(resp.headers["X-Request-ID"])
        assert len(ids) == 5


def test_main_app_has_request_id(client):
    """Main app includes X-Request-ID on responses."""
    resp = client.get("/v1/search?q=test")
    assert "X-Request-ID" in resp.headers
