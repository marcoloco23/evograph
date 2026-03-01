"""Tests for rate limiting middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from evograph.middleware.rate_limit import RateLimitMiddleware


def test_rate_limit_headers_on_api(client):
    """API endpoints include rate limit headers."""
    resp = client.get("/v1/search?q=test")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" in resp.headers
    assert resp.headers["X-RateLimit-Limit"] == "100"
    assert int(resp.headers["X-RateLimit-Remaining"]) >= 0


def test_rate_limit_decrements(client):
    """Remaining count decreases with each request."""
    resp1 = client.get("/v1/search?q=test")
    remaining1 = int(resp1.headers["X-RateLimit-Remaining"])

    resp2 = client.get("/v1/search?q=test")
    remaining2 = int(resp2.headers["X-RateLimit-Remaining"])

    assert remaining2 == remaining1 - 1


def test_health_excluded_from_main_app():
    """Health endpoint on the main app has no rate limit headers."""
    from evograph.main import app

    with TestClient(app) as c:
        resp = c.get("/health")
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" not in resp.headers


def test_rate_limit_429_when_exceeded():
    """Returns 429 when rate limit is exceeded."""
    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, max_requests=3, window_seconds=60)

    @test_app.get("/test")
    def test_endpoint():
        return {"ok": True}

    with TestClient(test_app) as c:
        for _ in range(3):
            resp = c.get("/test")
            assert resp.status_code == 200

        resp = c.get("/test")
        assert resp.status_code == 429
        assert resp.json()["detail"] == "Too many requests"
        assert "Retry-After" in resp.headers


def test_excluded_paths_not_counted():
    """Excluded paths don't consume rate limit budget."""
    test_app = FastAPI()
    test_app.add_middleware(
        RateLimitMiddleware,
        max_requests=2,
        window_seconds=60,
        exclude_paths=("/health",),
    )

    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    @test_app.get("/api")
    def api():
        return {"data": True}

    with TestClient(test_app) as c:
        # Health should always work and not count
        for _ in range(10):
            resp = c.get("/health")
            assert resp.status_code == 200

        # API should still have its full budget
        resp = c.get("/api")
        assert resp.status_code == 200
        resp = c.get("/api")
        assert resp.status_code == 200
        # Third should be blocked
        resp = c.get("/api")
        assert resp.status_code == 429
