from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str
    model: Optional[str] = None
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 1024

    system_prompt: Optional[str] = None


class ChatResponseChunk(BaseModel):
    conversation_id: Optional[int] = None
    delta: str
    done: bool = False


class ConversationCreateResponse(BaseModel):
    conversation_id: int


class ConversationListItem(BaseModel):
    id: int
    title: str
    model: str
    updated_at: str


class ConversationDeleteResponse(BaseModel):
    deleted: bool


class ModelListResponse(BaseModel):
    models: List[str]


class ShareCreateRequest(BaseModel):
    conversation_id: int
    is_public: bool = True

class ShareResponse(BaseModel):
    share_id: str
    share_url: str

class ShareViewResponse(BaseModel):
    share_id: str
    title: str
    messages: List[ChatMessage]

class UserBase(BaseModel):
    name: Optional[str] = None
    email: str
    profile_picture: Optional[str] = None

class User(UserBase):
    id: int
    google_id: str
    created_at: datetime
    last_login: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User

class GoogleLoginRequest(BaseModel):
    credential: str
