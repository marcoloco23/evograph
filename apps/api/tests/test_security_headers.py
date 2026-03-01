"""Tests for security headers middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from evograph.middleware.security_headers import SecurityHeadersMiddleware


def test_security_headers_present():
    """All security headers are set on responses."""
    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware)

    @test_app.get("/test")
    def test_endpoint():
        return {"ok": True}

    with TestClient(test_app) as c:
        resp = c.get("/test")
        assert resp.status_code == 200
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["X-XSS-Protection"] == "1; mode=block"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in resp.headers["Permissions-Policy"]


def test_security_headers_on_main_app():
    """Security headers appear on the main app's endpoints."""
    from evograph.main import app

    with TestClient(app) as c:
        resp = c.get("/health")
        assert resp.status_code == 200
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
