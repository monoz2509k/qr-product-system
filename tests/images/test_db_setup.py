from sqlalchemy import text


def test_stub_product_defaults(db):
    with db.begin() as session:
        session.execute(text("INSERT INTO product (vendor_id) VALUES (1)"))
    with db() as session:
        row = session.execute(text("SELECT status, version FROM product")).one()
    assert tuple(row) == ("ACTIVE", 1)


def test_reset_clears_rows_and_identity(db, reset_tables):
    with db.begin() as session:
        session.execute(text("INSERT INTO product (vendor_id) VALUES (1), (2)"))
    reset_tables()
    with db.begin() as session:
        assert session.scalar(text("SELECT count(*) FROM product")) == 0
        new_id = session.scalar(
            text("INSERT INTO product (vendor_id) VALUES (3) RETURNING id")
        )
    assert new_id == 1
