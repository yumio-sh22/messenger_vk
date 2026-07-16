from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import get_current_user, require_chat_member
from app.models import Attachment, Chat, ChatMember, ChatType, MemberRole, Message, MessageReadReceipt, MessageStatus, User
from app.schemas import ChatCreate, ChatMemberCreate, ChatMemberRead, ChatMemberUpdate, ChatRead

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
    if membership.role == MemberRole.owner:
        return membership
    raise HTTPException(status_code=403, detail="Управлять участниками может только админ группы")


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


def chat_display_for_user(db: Session, chat: Chat, user: User | None) -> tuple[str | None, str | None]:
    if not user or chat.type != ChatType.direct or chat.title == "Избранное":
        return None, None
    row = db.execute(
        select(ChatMember, User)
        .join(User, User.id == ChatMember.user_id)
        .where(ChatMember.chat_id == chat.id, ChatMember.user_id != user.id)
        .limit(1)
    ).first()
    if not row:
        return None, None
    _, peer = row
    return sender_label(peer, peer.id), peer.avatar_url


def chat_preview(db: Session, chat: Chat, user: User | None = None) -> ChatRead:
    member_count = db.scalar(select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat.id)) or 0
    display_title, display_avatar_url = chat_display_for_user(db, chat, user)
    row = db.execute(
        select(Message, User)
        .join(User, User.id == Message.sender_id)
        .where(Message.chat_id == chat.id)
        .where(Message.is_deleted.is_(False))
        .order_by(Message.created_at.desc())
        .limit(1)
    ).first()
    if not row:
        data = ChatRead.model_validate(chat)
        data.member_count = member_count
        data.display_title = display_title
        data.display_avatar_url = display_avatar_url
        return data

    message, sender = row
    has_attachments = bool(db.scalar(select(Attachment.id).where(Attachment.message_id == message.id).limit(1)))
    last_body = "Файл" if message.body == "\u2060" and has_attachments else message.body
    if chat.title == "Избранное" and message.reply_to_message_id:
        source = db.get(Message, message.reply_to_message_id)
        source_has_attachments = bool(source and db.scalar(select(Attachment.id).where(Attachment.message_id == source.id).limit(1)))
        source_body = source.body if source else None
        if source_body:
            last_body = "Файл" if source_body == "\u2060" and source_has_attachments else source_body
    return ChatRead(
        id=chat.id,
        title=chat.title,
        type=chat.type,
        created_by_id=chat.created_by_id,
        created_at=chat.created_at,
        display_title=display_title,
        display_avatar_url=display_avatar_url,
        last_message_body=last_body,
        last_message_sender_id=message.sender_id,
        last_message_sender_name=sender_label(sender, message.sender_id),
        last_message_status=message_status(db, message, member_count),
        last_message_created_at=message.created_at,
        member_count=member_count,
    )


@router.get("", response_model=list[ChatRead])
def list_chats(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ChatRead]:
    get_or_create_saved_chat(db, user)
    query = (
        select(Chat)
        .join(ChatMember)
        .where(ChatMember.user_id == user.id)
        .where(ChatMember.is_hidden.is_(False))
        .order_by(Chat.created_at.desc())
    )
    chats = [chat_preview(db, chat, user) for chat in db.scalars(query)]
    return sorted(chats, key=lambda chat: chat.last_message_created_at or chat.created_at, reverse=True)


@router.get("/saved", response_model=ChatRead)
def saved_chat(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Chat:
    return chat_preview(db, get_or_create_saved_chat(db, user), user)


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Chat:
    if payload.type == ChatType.direct and len(payload.members) != 1:
        raise HTTPException(status_code=400, detail="Для личного чата нужен ровно один собеседник")
    if payload.type == ChatType.group and not payload.members:
        raise HTTPException(status_code=400, detail="Для группы нужен хотя бы один участник")
    if payload.type == ChatType.direct:
        peer_id = payload.members[0].user_id
        existing_direct = db.scalar(
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(Chat.type == ChatType.direct, ChatMember.user_id == user.id)
            .where(
                Chat.id.in_(
                    select(ChatMember.chat_id).where(ChatMember.user_id == peer_id)
                )
            )
        )
        if existing_direct:
            own_member = db.scalar(
                select(ChatMember).where(ChatMember.chat_id == existing_direct.id, ChatMember.user_id == user.id)
            )
            if own_member and own_member.is_hidden:
                own_member.is_hidden = False
                write_audit(db, user.id, "restore_direct_chat", "chat", existing_direct.id)
                db.commit()
                db.refresh(existing_direct)
            return chat_preview(db, existing_direct, user)
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
            raise HTTPException(status_code=404, detail=f"Пользователь {member.user_id} не найден")
        db.add(ChatMember(chat_id=chat.id, user_id=member.user_id, role=MemberRole.member))
        added.add(member.user_id)

    write_audit(db, user.id, "create_chat", "chat", chat.id)
    db.commit()
    db.refresh(chat)
    return chat_preview(db, chat, user)


@router.get("/{chat_id}", response_model=ChatRead)
def get_chat(chat_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Chat:
    require_chat_member(db, chat_id, user)
    chat = db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return chat_preview(db, chat, user)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: int,
    scope: str = Query(default="me", pattern="^(me|all)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    membership = require_chat_member(db, chat_id, user)
    chat = db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    if chat.title == "Избранное" and chat.created_by_id == user.id:
        raise HTTPException(status_code=400, detail="Избранное нельзя удалить")

    if chat.type == ChatType.direct and scope == "me":
        membership.is_hidden = True
        write_audit(db, user.id, "hide_direct_chat", "chat", chat_id)
        db.commit()
        return

    if chat.type == ChatType.group and scope == "me":
        if membership.role == MemberRole.owner:
            owner_count = db.scalar(
                select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat_id, ChatMember.role == MemberRole.owner)
            ) or 0
            if owner_count <= 1:
                raise HTTPException(status_code=400, detail="Перед выходом назначьте другого админа группы")
        db.delete(membership)
        write_audit(db, user.id, "leave_group", "chat", chat_id)
        db.commit()
        return

    if chat.type == ChatType.group and membership.role != MemberRole.owner:
        raise HTTPException(status_code=403, detail="Удалить группу может только админ группы")

    db.delete(chat)
    write_audit(db, user.id, "delete_chat_for_all", "chat", chat_id)
    db.commit()


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
            display_name=member_user.display_name,
            avatar_url=member_user.avatar_url,
            city=member_user.city,
            age=member_user.age,
            status_text=member_user.status_text,
            is_online=member_user.is_online,
            app_role=member_user.role,
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
        raise HTTPException(status_code=404, detail="Чат не найден")
    if chat.type != ChatType.group:
        raise HTTPException(status_code=400, detail="Участниками можно управлять только в группах")

    member_user = db.get(User, payload.user_id)
    if not member_user or not member_user.is_active:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    exists = db.scalar(select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == payload.user_id))
    if exists:
        raise HTTPException(status_code=409, detail="Пользователь уже состоит в группе")

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
        display_name=member_user.display_name,
        avatar_url=member_user.avatar_url,
        city=member_user.city,
        age=member_user.age,
        status_text=member_user.status_text,
        is_online=member_user.is_online,
        app_role=member_user.role,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.patch("/{chat_id}/members/{user_id}", response_model=ChatMemberRead)
def update_member_role(
    chat_id: int,
    user_id: int,
    payload: ChatMemberUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMemberRead:
    require_chat_admin(db, chat_id, user)
    chat = db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    if chat.type != ChatType.group:
        raise HTTPException(status_code=400, detail="Роли можно менять только в группах")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Админ не может изменить свою роль")
    member = db.scalar(select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id))
    member_user = db.get(User, user_id)
    if not member or not member_user:
        raise HTTPException(status_code=404, detail="Участник чата не найден")
    if member.role == MemberRole.owner and payload.role != MemberRole.owner:
        owner_count = db.scalar(
            select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat_id, ChatMember.role == MemberRole.owner)
        ) or 0
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="В группе должен остаться хотя бы один админ")
    member.role = payload.role
    write_audit(db, user.id, "update_chat_member_role", "chat", chat_id, f"user_id={user_id};role={member.role}")
    db.commit()
    db.refresh(member)
    return ChatMemberRead(
        user_id=member.user_id,
        username=member_user.username,
        email=member_user.email,
        display_name=member_user.display_name,
        avatar_url=member_user.avatar_url,
        city=member_user.city,
        age=member_user.age,
        status_text=member_user.status_text,
        is_online=member_user.is_online,
        app_role=member_user.role,
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
        raise HTTPException(status_code=404, detail="Чат не найден")
    if chat.type != ChatType.group:
        raise HTTPException(status_code=400, detail="Участниками можно управлять только в группах")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Админ не может удалить себя")

    member = db.scalar(select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id))
    if not member:
        raise HTTPException(status_code=404, detail="Участник чата не найден")
    if member.role == MemberRole.owner:
        owner_count = db.scalar(
            select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat_id, ChatMember.role == MemberRole.owner)
        ) or 0
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Нельзя удалить единственного админа группы")

    db.delete(member)
    write_audit(db, user.id, "remove_chat_member", "chat", chat_id, f"user_id={user_id}")
    db.commit()
