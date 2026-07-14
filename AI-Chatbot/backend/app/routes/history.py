from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Conversation, Message, User
from ..auth import get_current_user

router = APIRouter(prefix="/api/history", tags=["history"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all conversations with message count and last message preview."""
    rows = db.query(Conversation).filter(Conversation.user_id == current_user.id).order_by(Conversation.updated_at.desc()).all()
    out = []
    for c in rows:
        # Count messages
        msg_count = (
            db.query(func.count(Message.id))
            .filter(Message.conversation_id == c.id)
            .scalar()
        ) or 0

        # Last assistant message preview (first 80 chars)
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == c.id, Message.role == "assistant")
            .order_by(Message.created_at.desc())
            .first()
        )
        preview = ""
        if last_msg and last_msg.content:
            preview = last_msg.content[:80].replace("\n", " ")

        out.append({
            "id":           c.id,
            "title":        c.title or "New chat",
            "model":        c.model,
            "updated_at":   str(c.updated_at),
            "message_count": msg_count,
            "preview":      preview,
        })
    return out


@router.get("/conversations/{conversation_id}")
def conversation_details(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        return {"error": "not found"}

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return {
        "id":            conv.id,
        "title":         conv.title,
        "model":         conv.model,
        "system_prompt": conv.system_prompt,
        "messages": [
            {
                "role":       m.role,
                "content":    m.content,
                "created_at": str(m.created_at),
            }
            for m in msgs
        ],
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        return {"error": "not found"}
    db.delete(conv)
    db.commit()
    return {"success": True}
