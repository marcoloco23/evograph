from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from evograph.api.routes import graph, search, sequences, stats, taxa
from evograph.middleware.rate_limit import RateLimitMiddleware
from evograph.middleware.request_logging import RequestLoggingMiddleware
from evograph.settings import settings

app = FastAPI(title="EvoGraph MVP", version="0.1.0")

# Middleware stack (order matters: outermost runs first)
# 1. Request logging — logs every request with method, path, status, duration
app.add_middleware(RequestLoggingMiddleware)

# 2. GZip responses > 500 bytes — critical for graph endpoints with large JSON payloads
app.add_middleware(GZipMiddleware, minimum_size=500)

# 3. Rate limiting: 100 requests/minute per IP (excludes /health, /docs)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# 4. CORS — configurable origins (default: allow all for dev)
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
    return {"status": "ok", "scope": settings.scope_ott_root}
