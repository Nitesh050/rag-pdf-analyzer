from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.security import hash_password
from src.db.session import get_db
from src.models.user import User
from src.schemas.auth import SignupRequest, UserResponse

router = APIRouter(prefix="/auth")


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

    return UserResponse(id=str(user.id), email=user.email, display_name=user.display_name)
