"""
Signup, login and logout through the real /auth endpoints and Postgres.
Needs TEST_DATABASE_URL (see README).
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.core.security import get_local_user, hash_token, verify_password
from src.db.session import get_db
from src.models.user import User, UserSession


@pytest.fixture
def client(db):
    from src.main import app

    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def signup(client, **overrides):
    body = {"email": "ada@example.com", "password": "correct horse", "display_name": "Ada", **overrides}
    return client.post("/auth/signup", json=body)


def test_signup_creates_user_with_hashed_password(client, db):
    response = signup(client)

    assert response.status_code == 201, response.text
    assert response.json()["email"] == "ada@example.com"
    assert "password" not in response.text  # neither the password nor its hash is returned

    user = db.scalar(select(User).where(User.email == "ada@example.com"))
    assert user.password_hash != "correct horse"
    assert verify_password("correct horse", user.password_hash)


def test_signup_rejects_duplicate_email_ignoring_case(client):
    assert signup(client).status_code == 201

    response = signup(client, email="ADA@Example.com")

    assert response.status_code == 409


@pytest.mark.parametrize("overrides", [
    {"email": "not-an-email"},
    {"password": "short"},
    {"password": "x" * 73},
])
def test_signup_rejects_invalid_input(client, overrides):
    assert signup(client, **overrides).status_code == 422


def login(client, email="ada@example.com", password="correct horse"):
    return client.post("/auth/login", json={"email": email, "password": password})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_a_token_that_identifies_the_user(client, db):
    signup(client)

    response = login(client, email="ADA@example.com")  # email case doesn't matter

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["email"] == "ada@example.com"
    token = body["access_token"]

    # Only the token's hash is stored.
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    assert session is not None
    assert session.user.last_login_at is not None

    me = client.get("/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"


@pytest.mark.parametrize("email, password", [
    ("ada@example.com", "wrong horse"),
    ("nobody@example.com", "correct horse"),
])
def test_login_failures_look_the_same(client, email, password):
    signup(client)

    response = login(client, email, password)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_nobody_can_log_in_as_the_local_user(client, db):
    get_local_user(db)

    assert login(client, email="local@localhost", password="!").status_code == 401


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer not-a-real-token"}])
def test_me_requires_a_valid_token(client, headers):
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_expired_session_is_rejected(client, db):
    signup(client)
    token = login(client).json()["access_token"]
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    session.created_at = datetime.now(timezone.utc) - timedelta(days=8)
    session.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.flush()

    assert client.get("/auth/me", headers=auth(token)).status_code == 401


def test_logout_revokes_the_token(client):
    signup(client)
    token = login(client).json()["access_token"]

    assert client.post("/auth/logout", headers=auth(token)).status_code == 204
    assert client.get("/auth/me", headers=auth(token)).status_code == 401
