"""
Database fixtures for tests/db. Tests are skipped unless TEST_DATABASE_URL
points at a Postgres with the schema from src/db/schema (see README.md).
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture(scope="module")
def engine():
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    engine = create_engine(DATABASE_URL)
    try:
        engine.connect().close()
    except OperationalError:
        pytest.skip(f"database not reachable at {DATABASE_URL}")
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()
