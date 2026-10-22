"""
ORM models against a real Postgres with the schema from src/db/schema.

Needs a database (see tests/db/README.md) and TEST_DATABASE_URL, e.g.
postgresql+psycopg://postgres:check@localhost:5433/rag. Skipped otherwise.
Every test runs in a transaction that is rolled back.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from src.models.base import Base
from src.models.chunk import Chunk
from src.models.conversation import Conversation, Message, MessageSource
from src.models.document import Document
from src.models.user import User, UserSession

def make_user(db, email="alice@example.com"):
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.flush()
    return user


@pytest.mark.parametrize("model", [User, UserSession, Document, Chunk, Conversation, Message, MessageSource])
def test_model_matches_database_table(engine, model):
    """Same columns and nullability as the table built from the SQL files."""
    table = model.__table__
    in_db = {c["name"]: c for c in inspect(engine).get_columns(table.name)}

    assert set(table.columns.keys()) == set(in_db)
    for column in table.columns:
        assert column.nullable == in_db[column.name]["nullable"], column.name


def test_database_fills_defaults(db):
    user = make_user(db)
    db.refresh(user)

    assert user.role == "user"
    assert user.is_active is True
    assert user.created_at is not None and user.updated_at is not None


def test_email_is_case_insensitive(db):
    make_user(db, email="Alice@Example.com")

    found = db.scalar(select(User).where(User.email == "alice@example.COM"))
    assert found is not None

    db.add(User(email="ALICE@example.com", password_hash="hash"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_invalid_role_is_rejected(db):
    db.add(User(email="bob@example.com", password_hash="hash", role="superuser"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_updated_at_is_set_by_trigger(db):
    user = make_user(db)
    old = datetime(2000, 1, 1, tzinfo=timezone.utc)
    user.updated_at = old
    db.flush()

    user.display_name = "Alice"
    db.flush()
    db.refresh(user)

    assert user.updated_at > old


def test_sessions_belong_to_user_and_are_deleted_with_it(db):
    user = make_user(db)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    user.sessions.append(UserSession(token_hash="t1", expires_at=expires, ip_address="10.0.0.1"))
    user.sessions.append(UserSession(token_hash="t2", expires_at=expires))
    db.flush()

    assert db.scalar(select(UserSession).where(UserSession.token_hash == "t1")).user is user

    db.delete(user)
    db.flush()
    assert db.scalars(select(UserSession)).all() == []


def test_session_validity(db):
    user = make_user(db)
    now = datetime.now(timezone.utc)
    live = UserSession(user=user, token_hash="live", expires_at=now + timedelta(hours=1))
    revoked = UserSession(user=user, token_hash="revoked", expires_at=now + timedelta(hours=1), revoked_at=now)
    db.add_all([live, revoked])
    db.flush()

    assert live.is_valid
    assert not revoked.is_valid


def test_session_cannot_expire_before_it_is_created(db):
    user = make_user(db)
    db.add(UserSession(user=user, token_hash="bad", expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc)))
    with pytest.raises(IntegrityError):
        db.flush()


def test_all_models_share_one_metadata():
    expected = {"users", "sessions", "documents", "chunks", "conversations", "messages", "message_sources"}
    assert expected <= set(Base.metadata.tables)
