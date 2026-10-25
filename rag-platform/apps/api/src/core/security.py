import hashlib
import secrets
from datetime import timedelta

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.user import User, UserSession

# Owner for documents indexed before accounts existed (see
# db/backfill_documents.py). Its password hash can't match any password,
# so nobody can log in as it.
LOCAL_USER_EMAIL = "local@localhost"
UNUSABLE_PASSWORD = "!"

SESSION_LIFETIME = timedelta(days=7)

# auto_error=False so a missing header gets our 401, not FastAPI's 403.
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    # gensalt() picks a random salt per password, so two users with the
    # same password still get different hashes.
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        # Not a bcrypt hash, e.g. UNUSABLE_PASSWORD.
        return False


# Checked against when the email is unknown, so a login attempt takes as
# long for a missing account as for a wrong password and doesn't reveal
# which emails are registered.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # A plain SHA-256 is enough here: unlike passwords, tokens are 256 random
    # bits, so there is nothing to brute-force. bcrypt would only slow every request.
    return hashlib.sha256(token.encode()).hexdigest()


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> UserSession:
    """
    FastAPI dependency: the login session for the request's
    "Authorization: Bearer <token>" header, or 401.
    """
    session = None
    if credentials:
        session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(credentials.credentials)))

    if session is None or not session.is_valid or not session.user.is_active:
        raise HTTPException(status_code=401, detail="Not logged in.", headers={"WWW-Authenticate": "Bearer"})
    return session


def get_local_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == LOCAL_USER_EMAIL))
    if user:
        return user

    try:
        with db.begin_nested():
            user = User(email=LOCAL_USER_EMAIL, password_hash=UNUSABLE_PASSWORD, display_name="Local user")
            db.add(user)
        db.commit()
        return user
    except IntegrityError:
        # Another request created it at the same moment.
        db.rollback()
        return db.scalar(select(User).where(User.email == LOCAL_USER_EMAIL))


def get_current_user(session: UserSession = Depends(get_current_session)) -> User:
    """
    FastAPI dependency for "who is asking": the logged-in user, or 401.
    """
    return session.user
