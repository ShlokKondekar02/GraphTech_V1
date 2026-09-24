"""
pytest fixtures: overridden DB using a clean in-memory SQLite database.

We can't use SQLite directly with JSONB and Vector column types (Postgres-specific).
Solution: monkey-patch those columns to use SQLite-compatible JSON/Text types
*before* metadata.create_all() is called. This is done purely in tests — the
real models remain unchanged.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Text, JSON
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_db
from app.models.base import Base


SQLITE_URL = "sqlite:///./test_sprint0.db"


def _patch_postgres_types():
    """
    Replace PostgreSQL-only column types (JSONB, Vector) with SQLite-compatible
    equivalents so that Base.metadata.create_all() succeeds on SQLite.
    Only called once before table creation.
    """
    from app.models import diagram_requests as dr_mod
    from app.models import users  # noqa: F401 — ensure User is loaded

    table = dr_mod.DiagramRequest.__table__

    # Replace Vector(1024) → Text
    emb_col = table.c.get("embedding")
    if emb_col is not None:
        emb_col.type = Text()

    # Replace JSONB → JSON (SQLite has native JSON support via sqlite3)
    sj_col = table.c.get("structured_json")
    if sj_col is not None:
        sj_col.type = JSON()


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh SQLite database for each test function."""
    _patch_postgres_types()

    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Yield a test DB session bound to the SQLite test engine."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with the get_db dependency overridden to use the test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # follow_redirects=False so we can inspect 3xx responses
    with TestClient(app, raise_server_exceptions=True, follow_redirects=False) as c:
        yield c
    app.dependency_overrides.clear()
