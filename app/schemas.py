from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import ChatType, MemberRole, MessageStatus, UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.writer


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: str
    role: UserRole
    display_name: str | None = None
    avatar_url: str | None = None
    city: str | None = None
    age: int | None = None
    status_text: str | None = None
    is_online: bool = True
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=2_000_000)
    city: str | None = Field(default=None, max_length=120)
    age: int | None = Field(default=None, ge=0, le=130)
    status_text: str | None = Field(default=None, max_length=160)
    is_online: bool = True


class UserPresenceUpdate(BaseModel):
    is_online: bool


class ChatMemberCreate(BaseModel):
    user_id: int
    role: MemberRole = MemberRole.member


class ChatMemberRead(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    app_role: UserRole
    role: MemberRole
    joined_at: datetime


class ChatCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    type: ChatType = ChatType.group
    members: list[ChatMemberCreate] = []


class ChatRead(BaseModel):
    id: int
    title: str
    type: ChatType
    created_by_id: int
    created_at: datetime
    last_message_body: str | None = None
    last_message_sender_id: int | None = None
    last_message_sender_name: str | None = None
    last_message_status: MessageStatus | None = None
    last_message_created_at: datetime | None = None

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    reply_to_message_id: int | None = None


class MessageUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class MessageRead(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    sender_name: str | None = None
    sender_username: str | None = None
    reply_to_message_id: int | None = None
    source_chat_id: int | None = None
    source_message_id: int | None = None
    source_chat_title: str | None = None
    source_sender_name: str | None = None
    is_forwarded: bool = False
    body: str
    status: MessageStatus
    read_by_count: int = 0
    chat_member_count: int = 0
    is_favorite: bool = False
    is_deleted: bool = False
    created_at: datetime
    edited_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReactionCreate(BaseModel):
    emoji: str = Field(min_length=1, max_length=16)


class AttachmentCreate(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_url: str = Field(min_length=1, max_length=1000)
    mime_type: str | None = Field(default=None, max_length=120)
