import pytest
from sqlalchemy import text

# Stand-in for TV2's product table until their migration exists.
STUB_PRODUCT = """
CREATE TABLE product (
  id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  vendor_id BIGINT NOT NULL,
  status    TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'DELETED')),
  version   INTEGER NOT NULL DEFAULT 1
)
"""


@pytest.fixture(scope="session")
def image_schema(db_engine):
    with db_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS product CASCADE"))
        conn.execute(text(STUB_PRODUCT))


@pytest.fixture
def reset_tables(image_schema, db_engine):
    def reset():
        with db_engine.begin() as conn:
            conn.execute(text("TRUNCATE product RESTART IDENTITY CASCADE"))

    return reset


@pytest.fixture
def db(reset_tables, session_factory):
    reset_tables()
    return session_factory
