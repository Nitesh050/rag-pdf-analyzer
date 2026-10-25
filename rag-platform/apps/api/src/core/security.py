import bcrypt
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.user import User

# Until login exists, every request acts as this one user. Its password hash
# can't match any password, so nobody can log in as it.
LOCAL_USER_EMAIL = "local@localhost"
UNUSABLE_PASSWORD = "!"


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


def get_current_user(db: Session = Depends(get_db)) -> User:
    """
    FastAPI dependency for "who is asking". Returns the local user for now;
    replace with token authentication when login is added.
    """
    return get_local_user(db)
