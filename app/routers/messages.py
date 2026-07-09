from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.config import settings
from app.database import SessionLocal, get_db
from app.deps import get_current_user, require_chat_member, require_writer
from app.models import Attachment, Chat, ChatMember, ChatType, FavoriteMessage, MemberRole, Message, MessageStatus, Reaction, User
from app.schemas import AttachmentCreate, MessageCreate, MessageRead, MessageUpdate, ReactionCreate
from app.security import decode_access_token
from app.ws import manager

router = APIRouter(tags=["messages"])
send_windows: dict[int, deque[datetime]] = defaultdict(deque)


def check_rate_limit(user_id: int) -> None:
    now = datetime.now(UTC)
    window = send_windows[user_id]
    while window and now - window[0] > timedelta(minutes=1):
        window.popleft()
    if len(window) >= settings.rate_limit_messages_per_minute:
        raise HTTPException(status_code=429, detail="Message rate limit exceeded")
    window.append(now)


def ensure_can_write(member: ChatMember) -> None:
    if member.role == MemberRole.readonly:
        raise HTTPException(status_code=403, detail="Readonly chat member cannot send messages")


def get_saved_chat(db: Session, user: User) -> Chat:
    chat = db.scalar(
        select(Chat)
        .join(ChatMember)
        .where(ChatMember.user_id == user.id, Chat.title == "Избранное", Chat.created_by_id == user.id)
    )
    if chat:
        return chat
    chat = Chat(title="Избранное", type=ChatType.direct, created_by_id=user.id)
    db.add(chat)
    db.flush()
    db.add(ChatMember(chat_id=chat.id, user_id=user.id, role=MemberRole.owner))
    return chat


def public_message(message: Message) -> Message:
    if message.is_deleted:
        message.body = "Сообщение удалено"
    return message


@router.get("/api/chats/{chat_id}/messages", response_model=list[MessageRead])
def list_messages(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Message]:
    require_chat_member(db, chat_id, user)
    query = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.desc()).limit(limit)
    return [public_message(message) for message in reversed(db.scalars(query).all())]


@router.post("/api/chats/{chat_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: int,
    payload: MessageCreate,
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> Message:
    member = require_chat_member(db, chat_id, user)
    ensure_can_write(member)
    check_rate_limit(user.id)

    if payload.reply_to_message_id:
        parent = db.get(Message, payload.reply_to_message_id)
        if not parent or parent.chat_id != chat_id:
            raise HTTPException(status_code=404, detail="Reply message not found in this chat")

    message = Message(
        chat_id=chat_id,
        sender_id=user.id,
        reply_to_message_id=payload.reply_to_message_id,
        body=payload.body,
        status=MessageStatus.sent,
    )
    db.add(message)
    db.flush()
    write_audit(db, user.id, "send_message", "message", message.id)
    db.commit()
    db.refresh(message)

    await manager.broadcast(
        chat_id,
        {
            "event": "message.created",
            "message": MessageRead.model_validate(message).model_dump(mode="json"),
        },
    )
    return message


@router.get("/api/messages/search", response_model=list[MessageRead])
def search_messages(
    q: str = Query(min_length=1, max_length=120),
    chat_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Message]:
    pattern = f"%{q}%"
    query = (
        select(Message)
        .join(ChatMember, ChatMember.chat_id == Message.chat_id)
        .where(ChatMember.user_id == user.id)
        .where(Message.is_deleted.is_(False))
        .where(or_(Message.body.ilike(pattern), func.similarity(Message.body, q) > 0.2))
        .order_by(Message.created_at.desc())
        .limit(100)
    )
    if chat_id:
        require_chat_member(db, chat_id, user)
        query = query.where(Message.chat_id == chat_id)
    return list(db.scalars(query))


@router.patch("/api/messages/{message_id}", response_model=MessageRead)
async def edit_message(
    message_id: int,
    payload: MessageUpdate,
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> Message:
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    require_chat_member(db, message.chat_id, user)
    if message.sender_id != user.id:
        raise HTTPException(status_code=403, detail="Only sender can edit message")
    if message.is_deleted:
        raise HTTPException(status_code=400, detail="Deleted message cannot be edited")

    message.body = payload.body
    message.edited_at = datetime.now(UTC)
    write_audit(db, user.id, "edit_message", "message", message.id)
    db.commit()
    db.refresh(message)
    await manager.broadcast(
        message.chat_id,
        {"event": "message.updated", "message": MessageRead.model_validate(message).model_dump(mode="json")},
    )
    return message


@router.delete("/api/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    require_chat_member(db, message.chat_id, user)
    if message.sender_id != user.id:
        raise HTTPException(status_code=403, detail="Only sender can delete message")

    message.is_deleted = True
    message.body = "Сообщение удалено"
    write_audit(db, user.id, "delete_message", "message", message.id)
    db.commit()
    await manager.broadcast(message.chat_id, {"event": "message.deleted", "message_id": message.id})


@router.post("/api/messages/{message_id}/favorite", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def add_to_favorites(
    message_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    message = db.get(Message, message_id)
    if not message or message.is_deleted:
        raise HTTPException(status_code=404, detail="Message not found")
    require_chat_member(db, message.chat_id, user)

    exists = db.scalar(
        select(FavoriteMessage).where(FavoriteMessage.user_id == user.id, FavoriteMessage.message_id == message_id)
    )
    if not exists:
        db.add(FavoriteMessage(user_id=user.id, message_id=message_id))

    saved_chat = get_saved_chat(db, user)
    saved_copy = Message(
        chat_id=saved_chat.id,
        sender_id=user.id,
        body=f"Избранное из чата #{message.chat_id}: {message.body}",
        status=MessageStatus.sent,
        reply_to_message_id=message.id,
    )
    db.add(saved_copy)
    db.flush()
    write_audit(db, user.id, "favorite_message", "message", message.id)
    db.commit()
    db.refresh(saved_copy)
    return saved_copy


@router.post("/api/messages/{message_id}/reactions", status_code=status.HTTP_201_CREATED)
def add_reaction(
    message_id: int,
    payload: ReactionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    require_chat_member(db, message.chat_id, user)

    exists = db.scalar(
        select(Reaction).where(
            Reaction.message_id == message_id,
            Reaction.user_id == user.id,
            Reaction.emoji == payload.emoji,
        )
    )
    if not exists:
        db.add(Reaction(message_id=message_id, user_id=user.id, emoji=payload.emoji))
        write_audit(db, user.id, "add_reaction", "message", message_id, payload.emoji)
        db.commit()
    return {"status": "ok"}


@router.post("/api/messages/{message_id}/attachments", status_code=status.HTTP_201_CREATED)
def add_attachment(
    message_id: int,
    payload: AttachmentCreate,
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    member = require_chat_member(db, message.chat_id, user)
    ensure_can_write(member)
    db.add(
        Attachment(
            message_id=message_id,
            file_name=payload.file_name,
            file_url=payload.file_url,
            mime_type=payload.mime_type,
        )
    )
    write_audit(db, user.id, "add_attachment", "message", message_id, payload.file_name)
    db.commit()
    return {"status": "ok"}


@router.websocket("/ws/chats/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: int, token: str) -> None:
    user_id = decode_access_token(token)
    if not user_id:
        await websocket.close(code=1008)
        return

    with SessionLocal() as db:
        member = db.scalar(
            select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == int(user_id))
        )
        if not member:
            await websocket.close(code=1008)
            return

    await manager.connect(chat_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)
