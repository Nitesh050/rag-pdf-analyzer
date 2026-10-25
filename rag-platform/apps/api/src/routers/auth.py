import ipaddress
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.security import (
    DUMMY_PASSWORD_HASH,
    SESSION_LIFETIME,
    get_current_session,
    hash_password,
    hash_token,
    new_session_token,
    verify_password,
)
from src.db.session import get_db
from src.models.user import User, UserSession
from src.schemas.auth import LoginRequest, LoginResponse, SignupRequest, UserResponse

router = APIRouter(prefix="/auth")


def user_response(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), email=user.email, display_name=user.display_name)


def client_ip(request: Request) -> str | None:
    # sessions.ip_address is inet, so anything that isn't an IP (e.g. the
    # test client's "testclient") is stored as NULL rather than failing.
    host = request.client.host if request.client else None
    try:
        return str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        return None


@router.post("/signup", response_model=UserResponse, status_code=201)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # users.email is unique (and citext, so case is ignored).
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    return user_response(user)


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == request.email))
    password_ok = verify_password(request.password, user.password_hash if user else DUMMY_PASSWORD_HASH)

    # One message for every failure, so it doesn't reveal which emails exist.
    if not (user and password_ok and user.is_active):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    # The client gets the token; the database only ever sees its hash.
    token = new_session_token()
    now = datetime.now(timezone.utc)
    db.add(UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        user_agent=http_request.headers.get("user-agent"),
        ip_address=client_ip(http_request),
        expires_at=now + SESSION_LIFETIME,
    ))
    user.last_login_at = now
    db.commit()

    return LoginResponse(access_token=token, user=user_response(user))


@router.get("/me", response_model=UserResponse)
def me(session: UserSession = Depends(get_current_session)):
    return user_response(session.user)


@router.post("/logout", status_code=204)
def logout(session: UserSession = Depends(get_current_session), db: Session = Depends(get_db)):
    # Revoked rather than deleted, so the sessions table keeps a login history.
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
