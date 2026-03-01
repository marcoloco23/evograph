import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from evograph.api.routes import graph, search, sequences, stats, taxa
from evograph.db.session import SessionLocal, engine
from evograph.logging_config import configure_logging
from evograph.middleware.rate_limit import RateLimitMiddleware
from evograph.middleware.request_logging import RequestLoggingMiddleware
from evograph.middleware.security_headers import SecurityHeadersMiddleware
from evograph.settings import settings

configure_logging()
logger = logging.getLogger("evograph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle for the application.

    Ensures database connection pool is properly disposed on shutdown,
    preventing connection leaks in orchestrated deployments.
    """
    logger.info("EvoGraph API starting up (scope=%s)", settings.scope_ott_root)
    yield
    logger.info("EvoGraph API shutting down — disposing connection pool")
    engine.dispose()


app = FastAPI(title="EvoGraph MVP", version="0.1.0", lifespan=lifespan)

# Middleware stack (order matters: outermost runs first)
# 1. Request logging — logs every request with method, path, status, duration
app.add_middleware(RequestLoggingMiddleware)

# 2. GZip responses > 500 bytes — critical for graph endpoints with large JSON payloads
app.add_middleware(GZipMiddleware, minimum_size=500)

# 3. Rate limiting: 100 requests/minute per IP (excludes /health, /docs)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# 4. Security headers — X-Content-Type-Options, X-Frame-Options, etc.
app.add_middleware(SecurityHeadersMiddleware)

# 5. CORS — configurable origins (default: allow all for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/v1")
app.include_router(taxa.router, prefix="/v1")
app.include_router(graph.router, prefix="/v1")
app.include_router(sequences.router, prefix="/v1")
app.include_router(stats.router, prefix="/v1")


@app.get("/health")
def health():
    """Basic liveness check."""
    return {"status": "ok", "scope": settings.scope_ott_root}


@app.get("/health/ready")
def readiness():
    """Readiness check — verifies database connectivity and reports pool stats.

    Use for Kubernetes readinessProbe or load balancer health checks.
    Returns pool size, checked-in/out connections, and overflow count.
    """
    # Verify DB is reachable
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception:
        db_ok = False

    pool = engine.pool
    status = "ok" if db_ok else "degraded"

    return {
        "status": status,
        "scope": settings.scope_ott_root,
        "database": {
            "connected": db_ok,
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        },
    }
