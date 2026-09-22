"""SQLAlchemy engine/session wiring (CLAUDE.md #15, #17)."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _normalize_database_url(url: str) -> str:
    """Managed Postgres providers (Render, Railway, Heroku, ...) hand out a connection
    string as `postgres://` or plain `postgresql://` - psycopg3 needs the driver named
    explicitly (`postgresql+psycopg://`) for SQLAlchemy to pick the right dialect. Any
    other scheme (e.g. `sqlite://`) passes through unchanged."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


_settings = get_settings()
engine = create_engine(_normalize_database_url(_settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
