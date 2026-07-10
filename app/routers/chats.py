from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import get_current_user, require_chat_member, require_writer
from app.models import Chat, ChatMember, ChatType, MemberRole, Message, MessageReadReceipt, MessageStatus, User, UserRole
from app.schemas import ChatCreate, ChatMemberCreate, ChatMemberRead, ChatRead

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


def require_chat_admin(db: Session, chat_id: int, user: User) -> ChatMember | None:
    membership = require_chat_member(db, chat_id, user)
    if user.role == UserRole.admin or membership.role == MemberRole.owner:
        return membership
    raise HTTPException(status_code=403, detail="Only chat admin can manage members")


def sender_label(sender: User | None, fallback_id: int) -> str:
    if not sender:
        return f"user #{fallback_id}"
    return sender.display_name or sender.username or f"user #{sender.id}"


def message_status(db: Session, message: Message, member_count: int) -> MessageStatus:
    read_by_count = db.scalar(
        select(func.count(MessageReadReceipt.id)).where(MessageReadReceipt.message_id == message.id)
    ) or 0
    if member_count > 0 and read_by_count >= member_count:
        return MessageStatus.read
    if read_by_count > 1 or message.status == MessageStatus.delivered:
        return MessageStatus.delivered
    return MessageStatus.sent


def chat_preview(db: Session, chat: Chat) -> ChatRead:
    row = db.execute(
        select(Message, User)
        .join(User, User.id == Message.sender_id)
        .where(Message.chat_id == chat.id)
        .order_by(Message.created_at.desc())
        .limit(1)
    ).first()
    if not row:
        return ChatRead.model_validate(chat)

    message, sender = row
    member_count = db.scalar(select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat.id)) or 0
    return ChatRead(
        id=chat.id,
        title=chat.title,
        type=chat.type,
        created_by_id=chat.created_by_id,
        created_at=chat.created_at,
        last_message_body="Сообщение удалено" if message.is_deleted else message.body,
        last_message_sender_id=message.sender_id,
        last_message_sender_name=sender_label(sender, message.sender_id),
        last_message_status=message_status(db, message, member_count),
        last_message_created_at=message.created_at,
    )


@router.get("", response_model=list[ChatRead])
def list_chats(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ChatRead]:
    get_or_create_saved_chat(db, user)
    query = (
        select(Chat)
        .join(ChatMember)
        .where(ChatMember.user_id == user.id)
        .order_by(Chat.created_at.desc())
    )
    chats = [chat_preview(db, chat) for chat in db.scalars(query)]
    return sorted(chats, key=lambda chat: chat.last_message_created_at or chat.created_at, reverse=True)


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


@router.get("/{chat_id}/members", response_model=list[ChatMemberRead])
def list_members(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatMemberRead]:
    require_chat_member(db, chat_id, user)
    rows = db.execute(
        select(ChatMember, User)
        .join(User, User.id == ChatMember.user_id)
        .where(ChatMember.chat_id == chat_id)
        .order_by(ChatMember.role, User.username)
    ).all()
    return [
        ChatMemberRead(
            user_id=member.user_id,
            username=member_user.username,
            email=member_user.email,
            role=member.role,
            joined_at=member.joined_at,
        )
        for member, member_user in rows
    ]


@router.post("/{chat_id}/members", response_model=ChatMemberRead, status_code=status.HTTP_201_CREATED)
def add_member(
    chat_id: int,
    payload: ChatMemberCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMemberRead:
    require_chat_admin(db, chat_id, user)
    chat = db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.type != ChatType.group:
        raise HTTPException(status_code=400, detail="Members can be managed only in group chats")

    member_user = db.get(User, payload.user_id)
    if not member_user or not member_user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    exists = db.scalar(select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == payload.user_id))
    if exists:
        raise HTTPException(status_code=409, detail="User is already a chat member")

    member = ChatMember(chat_id=chat_id, user_id=payload.user_id, role=payload.role)
    db.add(member)
    db.flush()
    write_audit(db, user.id, "add_chat_member", "chat", chat_id, f"user_id={payload.user_id}")
    db.commit()
    db.refresh(member)
    return ChatMemberRead(
        user_id=member.user_id,
        username=member_user.username,
        email=member_user.email,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/{chat_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    chat_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    require_chat_admin(db, chat_id, user)
    chat = db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.type != ChatType.group:
        raise HTTPException(status_code=400, detail="Members can be managed only in group chats")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Admin cannot remove himself")

    member = db.scalar(select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id))
    if not member:
        raise HTTPException(status_code=404, detail="Chat member not found")

    db.delete(member)
    write_audit(db, user.id, "remove_chat_member", "chat", chat_id, f"user_id={user_id}")
    db.commit()
