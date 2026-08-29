"""
Yazmina Hijab Web — Database Engine & Session.

Uses PostgreSQL (Neon) as primary database.
SQLite for local development (path resolved relative to backend/).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import get_settings

settings = get_settings()

# For SQLite: resolve path relative to backend/ directory (not CWD)
_db_url = settings.DATABASE_URL
if _db_url.startswith("sqlite:///") and not _db_url.startswith("sqlite:////"):
    # Relative path — resolve against backend/ directory
    rel_path = _db_url.replace("sqlite:///", "")
    if not os.path.isabs(rel_path):
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        abs_path = os.path.join(backend_dir, rel_path)
        _db_url = f"sqlite:///{abs_path}"

engine = create_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db():
    """FastAPI dependency — yields a DB session, auto-closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
