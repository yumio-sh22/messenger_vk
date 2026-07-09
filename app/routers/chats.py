from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import get_current_user, require_chat_member, require_writer
from app.models import Chat, ChatMember, ChatType, MemberRole, User
from app.schemas import ChatCreate, ChatRead

router = APIRouter(prefix="/api/chats", tags=["chats"])


def get_or_create_saved_chat(db: Session, user: User) -> Chat:
    title = "Избранное"
    chat = db.scalar(
        select(Chat)
        .join(ChatMember)
        .where(ChatMember.user_id == user.id, Chat.title == title, Chat.created_by_id == user.id)
    )
    if chat:
        return chat

    chat = Chat(title=title, type=ChatType.direct, created_by_id=user.id)
    db.add(chat)
    db.flush()
    db.add(ChatMember(chat_id=chat.id, user_id=user.id, role=MemberRole.owner))
    write_audit(db, user.id, "create_saved_chat", "chat", chat.id)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("", response_model=list[ChatRead])
def list_chats(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Chat]:
    get_or_create_saved_chat(db, user)
    query = (
        select(Chat)
        .join(ChatMember)
        .where(ChatMember.user_id == user.id)
        .order_by(Chat.created_at.desc())
    )
    return list(db.scalars(query))


@router.get("/saved", response_model=ChatRead)
def saved_chat(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Chat:
    return get_or_create_saved_chat(db, user)


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> Chat:
    chat = Chat(title=payload.title, type=payload.type, created_by_id=user.id)
    db.add(chat)
    db.flush()

    db.add(ChatMember(chat_id=chat.id, user_id=user.id, role=MemberRole.owner))
    added = {user.id}
    for member in payload.members:
        if member.user_id in added:
            continue
        exists = db.scalar(select(User.id).where(User.id == member.user_id, User.is_active.is_(True)))
        if not exists:
            raise HTTPException(status_code=404, detail=f"User {member.user_id} not found")
        db.add(ChatMember(chat_id=chat.id, user_id=member.user_id, role=member.role))
        added.add(member.user_id)

    write_audit(db, user.id, "create_chat", "chat", chat.id)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("/{chat_id}", response_model=ChatRead)
def get_chat(chat_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Chat:
    require_chat_member(db, chat_id, user)
    chat = db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat
