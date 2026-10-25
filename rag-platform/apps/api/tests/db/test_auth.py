"""
Signup through the real /auth endpoints and Postgres. Needs TEST_DATABASE_URL
(see README).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.core.security import verify_password
from src.db.session import get_db
from src.models.user import User


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
