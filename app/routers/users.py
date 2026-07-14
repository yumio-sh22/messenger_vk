from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import User
from app.schemas import UserPresenceUpdate, UserProfileUpdate, UserRead, UserRoleUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if not user.is_online:
        user.is_online = True
        db.commit()
        db.refresh(user)
    return user


@router.patch("/me/profile", response_model=UserRead)
def update_profile(
    payload: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    field_limits = (
        (payload.display_name, 40, "Никнейм"),
        (payload.city, 80, "Город"),
        (payload.status_text, 120, "Статус"),
    )
    for value, limit, label in field_limits:
        if value is not None and len(value) > limit:
            raise HTTPException(status_code=400, detail=f"{label} нельзя писать длиннее {limit} символов")
    if payload.age is not None and (payload.age < 0 or payload.age > 200):
        raise HTTPException(status_code=400, detail="Возраст должен быть от 0 до 200 лет")
    user.display_name = payload.display_name
    user.avatar_url = payload.avatar_url
    user.city = payload.city
    user.age = payload.age
    user.status_text = payload.status_text
    user.is_online = payload.is_online
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/presence", response_model=UserRead)
def update_presence(
    payload: UserPresenceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user.is_online = payload.is_online
    db.commit()
    db.refresh(user)
    return user


@router.get("/contacts", response_model=list[UserRead])
def list_contacts(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.is_active.is_(True), User.id != user.id)
            .order_by(User.display_name, User.username)
        )
    )


@router.get("", response_model=list[UserRead])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


@router.patch("/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if not target or not target.is_active:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    target.role = payload.role
    write_audit(db, admin.id, "update_user_role", "user", target.id, f"role={payload.role}")
    db.commit()
    db.refresh(target)
    return target
