"""SQLAlchemy engine and session factory with connection pooling."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from evograph.settings import settings

# Normalize DATABASE_URL to use psycopg (v3) driver.
# Render provides postgres:// or postgresql://, but we need postgresql+psycopg://
_db_url = settings.database_url
if _db_url.startswith("postgres://"):
    _db_url = "postgresql+psycopg://" + _db_url[len("postgres://"):]
elif _db_url.startswith("postgresql://") and "+psycopg" not in _db_url:
    _db_url = "postgresql+psycopg://" + _db_url[len("postgresql://"):]

engine = create_engine(
    _db_url,
    # Connection pool configuration for production readiness
    pool_size=10,           # Maintain 10 persistent connections
    max_overflow=20,        # Allow up to 20 additional connections under load
    pool_recycle=300,       # Recycle connections after 5 minutes (avoid stale connections)
    pool_pre_ping=True,     # Verify connections are alive before using them
    pool_timeout=30,        # Wait up to 30s for a connection from the pool
    echo=False,             # Set True for SQL debugging
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
