import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..models import registry  # noqa: F401  (registers every model; see registry.py)

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:dev@localhost:5432/rag"


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


@lru_cache
def get_engine() -> Engine:
    """
    Process-wide engine, created on first use so importing this module
    never opens a connection (tests and scripts that don't touch the
    database work without one).
    """
    return create_engine(
        database_url(),
        pool_pre_ping=True,  # drop connections the server closed, e.g. after a DB restart
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """
    FastAPI dependency: one session per request, closed afterwards.

        def endpoint(db: Session = Depends(get_db)): ...
    """
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
