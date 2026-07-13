from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.models import User, UserRole
from app.schemas import Token, UserCreate, UserLogin, UserRead
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def verify_seed_password(db: Session, password: str, password_hash: str) -> bool:
    """Compatibility check for demo users created by PostgreSQL pgcrypto."""
    return bool(
        db.scalar(
            text("SELECT crypt(:password, :password_hash) = :password_hash"),
            {"password": password, "password_hash": password_hash},
        )
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    exists = db.scalar(select(User).where((User.email == payload.email) | (User.username == payload.username)))
    if exists:
        raise HTTPException(status_code=409, detail="Email or username already exists")

    user = User(
        email=str(payload.email),
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()
    write_audit(db, user.id, "register", "user", user.id)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == payload.email, User.is_active.is_(True)))
    password_ok = False
    if user:
        password_ok = verify_password(payload.password, user.password_hash)
        if not password_ok:
            password_ok = verify_seed_password(db, payload.password, user.password_hash)

    if not user or not password_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    write_audit(db, user.id, "login", "user", user.id)
    db.commit()
    return Token(access_token=create_access_token(str(user.id)))
