import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.config import settings

_url = make_url(settings.database_url)
TEST_DATABASE_URL = _url.set(database=f"{_url.database}_test")


def pytest_collection_modifyitems(items):
    for item in items:
        if "db_engine" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.db)


def _ensure_test_database():
    admin = create_engine(
        TEST_DATABASE_URL.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 2},
    )
    try:
        with admin.connect() as conn:
            name = TEST_DATABASE_URL.database
            if not conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}
            ):
                conn.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def db_engine():
    try:
        _ensure_test_database()
    except OperationalError as exc:
        if os.getenv("REQUIRE_DB"):
            raise
        pytest.skip(f"PostgreSQL unavailable ({exc.orig}); run `docker compose up -d`")
    engine = create_engine(TEST_DATABASE_URL, connect_args={"connect_timeout": 2})
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine)
