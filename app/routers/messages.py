from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.config import settings
from app.database import SessionLocal, get_db
from app.deps import get_current_user, require_chat_member, require_writer
from app.models import (
    Attachment,
    Chat,
    ChatMember,
    ChatType,
    FavoriteMessage,
    MemberRole,
    Message,
    MessageReadReceipt,
    MessageStatus,
    Reaction,
    User,
    UserRole,
)
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


def sender_label(sender: User | None, fallback_id: int) -> str:
    if not sender:
        return f"user #{fallback_id}"
    return sender.display_name or sender.username or f"user #{sender.id}"


def receipt_counts(db: Session, message_ids: list[int]) -> dict[int, int]:
    if not message_ids:
        return {}
    rows = db.execute(
        select(MessageReadReceipt.message_id, func.count(MessageReadReceipt.id))
        .where(MessageReadReceipt.message_id.in_(message_ids))
        .group_by(MessageReadReceipt.message_id)
    ).all()
    return {message_id: count for message_id, count in rows}


def favorite_message_ids(db: Session, user_id: int | None, message_ids: list[int]) -> set[int]:
    if not user_id or not message_ids:
        return set()
    return set(
        db.scalars(
            select(FavoriteMessage.message_id).where(
                FavoriteMessage.user_id == user_id,
                FavoriteMessage.message_id.in_(message_ids),
            )
        )
    )


def chat_member_count(db: Session, chat_id: int) -> int:
    return db.scalar(select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat_id)) or 0


def computed_status(message: Message, read_by_count: int, member_count: int) -> MessageStatus:
    if member_count > 0 and read_by_count >= member_count:
        return MessageStatus.read
    if read_by_count > 1 or message.status == MessageStatus.delivered:
        return MessageStatus.delivered
    return MessageStatus.sent


def message_read(
    message: Message,
    sender: User | None,
    read_by_count: int,
    member_count: int,
    is_favorite: bool = False,
    body_override: str | None = None,
    source_chat_id: int | None = None,
    source_message_id: int | None = None,
    source_chat_title: str | None = None,
    source_sender_name: str | None = None,
) -> MessageRead:
    return MessageRead(
        id=message.id,
        chat_id=message.chat_id,
        sender_id=message.sender_id,
        sender_name=sender_label(sender, message.sender_id),
        sender_username=sender.username if sender else None,
        reply_to_message_id=message.reply_to_message_id,
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
        source_chat_title=source_chat_title,
        source_sender_name=source_sender_name,
        is_forwarded=bool(source_chat_title),
        body="Сообщение удалено" if message.is_deleted else body_override or message.body,
        status=computed_status(message, read_by_count, member_count),
        read_by_count=read_by_count,
        chat_member_count=member_count,
        is_favorite=is_favorite,
        is_deleted=message.is_deleted,
        created_at=message.created_at,
        edited_at=message.edited_at,
    )


def mark_read(db: Session, user_id: int, messages: list[Message]) -> None:
    message_ids = [message.id for message in messages if message.id]
    if not message_ids:
        return
    existing_ids = set(
        db.scalars(
            select(MessageReadReceipt.message_id).where(
                MessageReadReceipt.user_id == user_id,
                MessageReadReceipt.message_id.in_(message_ids),
            )
        )
    )
    for message_id in message_ids:
        if message_id not in existing_ids:
            db.add(MessageReadReceipt(message_id=message_id, user_id=user_id))


def favorite_source_meta(db: Session, messages: list[Message]) -> dict[int, tuple[str, int, int, str, str]]:
    chat_ids = {message.chat_id for message in messages}
    saved_chat_ids = set(
        db.scalars(select(Chat.id).where(Chat.id.in_(chat_ids), Chat.title == "Избранное"))
    )
    candidates = [message for message in messages if message.chat_id in saved_chat_ids and message.reply_to_message_id]
    if not candidates:
        return {}
    parent_ids = [message.reply_to_message_id for message in candidates if message.reply_to_message_id]
    rows = db.execute(
        select(Message.id, Message.body, Message.chat_id, Chat.title, User)
        .join(Chat, Chat.id == Message.chat_id)
        .join(User, User.id == Message.sender_id)
        .where(Message.id.in_(parent_ids))
    ).all()
    sources = {
        message_id: (body, chat_id, message_id, title, sender_label(sender, sender.id))
        for message_id, body, chat_id, title, sender in rows
    }
    meta = {}
    for message in candidates:
        source = sources.get(message.reply_to_message_id)
        if not source:
            continue
        meta[message.id] = source
    return meta


def serialize_messages(
    db: Session,
    rows: list[tuple[Message, User]],
    mark_read_user_id: int | None = None,
    current_user_id: int | None = None,
) -> list[MessageRead]:
    messages = [message for message, _ in rows]
    if mark_read_user_id:
        mark_read(db, mark_read_user_id, messages)
        db.commit()
    counts = receipt_counts(db, [message.id for message in messages])
    favorites = favorite_message_ids(db, current_user_id or mark_read_user_id, [message.id for message in messages])
    source_meta = favorite_source_meta(db, messages)
    member_counts = {
        chat_id: chat_member_count(db, chat_id)
        for chat_id in {message.chat_id for message in messages}
    }
    return [
        message_read(
            message,
            sender,
            counts.get(message.id, 0),
            member_counts.get(message.chat_id, 0),
            message.id in favorites,
            source_meta.get(message.id, (None, None, None, None, None))[0],
            source_meta.get(message.id, (None, None, None, None, None))[1],
            source_meta.get(message.id, (None, None, None, None, None))[2],
            source_meta.get(message.id, (None, None, None, None, None))[3],
            source_meta.get(message.id, (None, None, None, None, None))[4],
        )
        for message, sender in rows
    ]


def serialize_message(
    db: Session,
    message: Message,
    sender: User | None = None,
    current_user_id: int | None = None,
) -> MessageRead:
    sender = sender or db.get(User, message.sender_id)
    counts = receipt_counts(db, [message.id])
    favorites = favorite_message_ids(db, current_user_id, [message.id])
    source_meta = favorite_source_meta(db, [message])
    source_body, source_chat_id, source_message_id, source_chat_title, source_sender_name = source_meta.get(
        message.id,
        (None, None, None, None, None),
    )
    return message_read(
        message,
        sender,
        counts.get(message.id, 0),
        chat_member_count(db, message.chat_id),
        message.id in favorites,
        source_body,
        source_chat_id,
        source_message_id,
        source_chat_title,
        source_sender_name,
    )


@router.get("/api/chats/{chat_id}/messages", response_model=list[MessageRead])
def list_messages(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    anchor_id: int | None = None,
    before_id: int | None = None,
) -> list[MessageRead]:
    require_chat_member(db, chat_id, user)
    anchor = db.get(Message, anchor_id) if anchor_id else None
    if anchor_id and (not anchor or anchor.chat_id != chat_id):
        raise HTTPException(status_code=404, detail="Source message not found")
    before = db.get(Message, before_id) if before_id else None
    if before_id and (not before or before.chat_id != chat_id):
        raise HTTPException(status_code=404, detail="Message page boundary not found")
    query = (
        select(Message, User)
        .join(User, User.id == Message.sender_id)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    if anchor:
        query = query.where(Message.created_at <= anchor.created_at)
    if before:
        query = query.where(Message.created_at < before.created_at)
    rows = list(reversed(db.execute(query).all()))
    return serialize_messages(db, rows, mark_read_user_id=user.id, current_user_id=user.id)


@router.post("/api/chats/{chat_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: int,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageRead:
    member = require_chat_member(db, chat_id, user)
    chat = db.get(Chat, chat_id)
    if user.role == UserRole.reader and (not chat or chat.title != "Избранное"):
        raise HTTPException(status_code=403, detail="Reader can send messages only in favorites")
    if user.role not in (UserRole.writer, UserRole.admin, UserRole.reader):
        raise HTTPException(status_code=403, detail="Write permission required")
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
    db.add(MessageReadReceipt(message_id=message.id, user_id=user.id))
    write_audit(db, user.id, "send_message", "message", message.id)
    db.commit()
    db.refresh(message)
    payload_message = serialize_message(db, message, user, current_user_id=user.id)

    await manager.broadcast(
        chat_id,
        {
            "event": "message.created",
            "message": payload_message.model_dump(mode="json"),
        },
    )
    return payload_message


@router.get("/api/messages/search", response_model=list[MessageRead])
def search_messages(
    q: str = Query(min_length=1, max_length=120),
    chat_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MessageRead]:
    pattern = f"%{q}%"
    query = (
        select(Message, User)
        .join(User, User.id == Message.sender_id)
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
    rows = db.execute(query).all()
    return serialize_messages(db, rows, mark_read_user_id=user.id, current_user_id=user.id)


@router.patch("/api/messages/{message_id}", response_model=MessageRead)
async def edit_message(
    message_id: int,
    payload: MessageUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageRead:
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    require_chat_member(db, message.chat_id, user)
    chat = db.get(Chat, message.chat_id)
    if user.role == UserRole.reader and (not chat or chat.title != "Избранное"):
        raise HTTPException(status_code=403, detail="Reader can edit messages only in favorites")
    if user.role not in (UserRole.writer, UserRole.admin, UserRole.reader):
        raise HTTPException(status_code=403, detail="Write permission required")
    if message.sender_id != user.id:
        raise HTTPException(status_code=403, detail="Only sender can edit message")
    if message.is_deleted:
        raise HTTPException(status_code=400, detail="Deleted message cannot be edited")
    if chat and chat.title == "Избранное" and message.reply_to_message_id:
        raise HTTPException(status_code=400, detail="Forwarded favorite messages cannot be edited")

    message.body = payload.body
    message.edited_at = datetime.now(UTC)
    write_audit(db, user.id, "edit_message", "message", message.id)
    db.commit()
    db.refresh(message)
    payload_message = serialize_message(db, message, current_user_id=user.id)
    await manager.broadcast(
        message.chat_id,
        {"event": "message.updated", "message": payload_message.model_dump(mode="json")},
    )
    return payload_message


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
    chat = db.get(Chat, message.chat_id)
    if user.role == UserRole.reader and (not chat or chat.title != "Избранное"):
        raise HTTPException(status_code=403, detail="Reader can delete messages only in favorites")

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
) -> MessageRead:
    message = db.get(Message, message_id)
    if not message or message.is_deleted:
        raise HTTPException(status_code=404, detail="Message not found")
    require_chat_member(db, message.chat_id, user)

    source_chat = db.get(Chat, message.chat_id)
    saved_chat = get_saved_chat(db, user)
    if source_chat and source_chat.id == saved_chat.id:
        raise HTTPException(status_code=400, detail="Message is already in favorites")

    exists = db.scalar(
        select(FavoriteMessage).where(FavoriteMessage.user_id == user.id, FavoriteMessage.message_id == message_id)
    )
    if exists:
        raise HTTPException(status_code=409, detail="Message is already in favorites")
    db.add(FavoriteMessage(user_id=user.id, message_id=message_id))

    saved_copy = Message(
        chat_id=saved_chat.id,
        sender_id=user.id,
        body=message.body,
        status=MessageStatus.sent,
        reply_to_message_id=message.id,
    )
    db.add(saved_copy)
    db.flush()
    db.add(MessageReadReceipt(message_id=saved_copy.id, user_id=user.id))
    write_audit(db, user.id, "favorite_message", "message", message.id)
    db.commit()
    db.refresh(saved_copy)
    return serialize_message(db, saved_copy, user, current_user_id=user.id)


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
