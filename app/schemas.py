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


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMemberCreate(BaseModel):
    user_id: int
    role: MemberRole = MemberRole.member


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
    reply_to_message_id: int | None = None
    body: str
    status: MessageStatus
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
