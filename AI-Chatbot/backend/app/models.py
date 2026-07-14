import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    profile_picture = Column(String)

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    last_login = Column(DateTime(timezone=True), default=_utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title = Column(String, default="New chat")
    model = Column(String, default="llama-3.1-8b-instant")

    system_prompt = Column(Text, default="")

    # Use Python-side defaults so SQLite actually updates these
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )

    role = Column(String)  # "user" | "assistant" | "system"
    content = Column(Text)

    created_at = Column(DateTime(timezone=True), default=_utcnow)


class Share(Base):
    __tablename__ = "shares"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_public = Column(Boolean, default=True)
