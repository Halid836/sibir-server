from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

class RegisterIn(BaseModel):
    email: EmailStr
    name: str
    username: str
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    name: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
    followers: int = 0
    following: int = 0

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None

class PostIn(BaseModel):
    text: str
    repost_of: int = 0

class PostOut(BaseModel):
    id: int
    author_id: int
    author_name: str
    author_username: str
    author_avatar: Optional[str] = None
    text: str
    likes: int
    repost_of: int
    created_at: datetime

class CommentIn(BaseModel):
    text: str

class CommentOut(BaseModel):
    id: int
    post_id: int
    author_id: int
    author_name: str
    author_username: str
    author_avatar: Optional[str] = None
    text: str
    created_at: datetime

class ChatOut(BaseModel):
    id: int
    other_id: int
    other_name: str
    other_username: str
    other_avatar: Optional[str] = None
    last_message: Optional[str] = None

class MessageIn(BaseModel):
    text: str

class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    sender_username: str
    text: str
    created_at: datetime

class ChannelIn(BaseModel):
    name: str
    username: str
    bio: Optional[str] = None
    avatar: Optional[str] = None

class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None

class ChannelOut(BaseModel):
    id: int
    name: str
    username: str
    bio: Optional[str] = None
    avatar: Optional[str] = None
    owner_id: int
    owner_username: str
    subscribers: int = 0
    is_subscribed: bool = False

class ChannelPostIn(BaseModel):
    text: str

class ChannelPostOut(BaseModel):
    id: int
    channel_id: int
    author_id: int
    author_username: str
    text: str
    likes: int
    created_at: datetime
    liked_by_me: bool = False

class ChannelCommentIn(BaseModel):
    text: str

class ChannelCommentOut(BaseModel):
    id: int
    post_id: int
    author_id: int
    author_name: str
    author_username: str
    text: str
    created_at: datetime

TokenOut.model_rebuild()