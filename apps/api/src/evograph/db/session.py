"""SQLAlchemy engine and session factory with connection pooling."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from evograph.settings import settings

engine = create_engine(
    settings.database_url,
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
