import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..ai import AVAILABLE_MODELS, MODEL_LABELS, DEFAULT_MODEL, stream_chat, auto_title
from ..database import SessionLocal
from ..models import Conversation, Message, User
from ..auth import get_current_user
from ..memory import conversation_to_messages
from ..rag import build_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Model listing ─────────────────────────────────────────────────────────────

@router.get("/models")
def list_models():
    return {
        "models":  AVAILABLE_MODELS,
        "labels":  MODEL_LABELS,
        "default": DEFAULT_MODEL,
    }


# ── Background: auto-title + DB update ───────────────────────────────────────

def _update_title_in_db(conversation_id: int, title: str) -> None:
    """Update conversation title in a fresh DB session (runs in background)."""
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            conv.title = title
            conv.updated_at = _utcnow()
            db.add(conv)
            db.commit()
    except Exception:
        logger.exception("Failed to update title for conversation %d", conversation_id)
    finally:
        db.close()


# ── Streaming chat endpoint ───────────────────────────────────────────────────

@router.post("/stream")
def chat_stream(req: schemas.ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Stream an AI response as NDJSON.

    Each line is a JSON object with one of:
      {"conversation_id": int, "delta": str, "done": false}
      {"conversation_id": int, "delta": "",  "done": true}
      {"conversation_id": int, "title": str, "done": false}   ← auto-title event
      {"conversation_id": int, "delta": "",  "done": true, "error": str}
    """
    # ── 1. Resolve / create conversation ─────────────────────────────────────
    conversation_id: Optional[int] = req.conversation_id
    is_new_conversation = conversation_id is None

    if is_new_conversation:
        conv = Conversation(
            title="New chat",
            model=req.model or DEFAULT_MODEL,
            system_prompt=req.system_prompt or "",
            user_id=current_user.id,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conversation_id = conv.id
    else:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv is None or conv.user_id != current_user.id:
            conv = Conversation(
                title="New chat",
                model=req.model or DEFAULT_MODEL,
                system_prompt=req.system_prompt or "",
                user_id=current_user.id,
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
            conversation_id = conv.id
            is_new_conversation = True

    # ── 2. Persist user message ───────────────────────────────────────────────
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)
    db.commit()

    # ── 3. Build message history (limit to last 40 rows) ─────────────────────
    rows: List[Message] = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(40)
        .all()
    )

    # Resolve system prompt (request > conversation > default)
    system_prompt = req.system_prompt if req.system_prompt is not None else conv.system_prompt
    if not system_prompt:
        system_prompt = (
            "You are a helpful, concise AI assistant. "
            "Provide clear, direct answers. "
            "Only elaborate when the user explicitly asks for more detail."
        )

    # ── 4. RAG context injection (sync, fast when no docs exist) ─────────────
    try:
        rag_context, citations = build_context(conversation_id, req.message)
    except Exception:
        rag_context, citations = "", []

    if rag_context:
        rag_prefix = (
            "Use the following document context to answer the user's question "
            "(cite the source when relevant):\n\n"
            f"{rag_context}\n\n---\n\n"
        )
        system_prompt = rag_prefix + system_prompt

    # ── 5. Build final messages payload (with truncation) ────────────────────
    raw_history = [{"role": m.role, "content": m.content} for m in rows]
    model = (req.model or conv.model or DEFAULT_MODEL).strip()
    messages = conversation_to_messages(system_prompt, raw_history)

    # ── 6. Capture IDs/values we need inside the async generator ─────────────
    _conv_id   = conversation_id
    _is_new    = is_new_conversation
    _user_msg  = req.message

    # ── 7. SSE generator ──────────────────────────────────────────────────────
    async def _events() -> AsyncIterator[bytes]:
        assistant_text = ""

        # Emit conversation_id immediately so the frontend can bind it
        yield (
            json.dumps({"conversation_id": _conv_id, "delta": "", "done": False})
            + "\n"
        ).encode()

        try:
            if not model:
                raise ValueError("No model resolved for this conversation.")
            if model not in AVAILABLE_MODELS:
                raise ValueError(
                    f"Model '{model}' is not available. "
                    f"Choose one of: {', '.join(AVAILABLE_MODELS)}"
                )

            async for delta in stream_chat(
                messages=messages,
                model=model,
                temperature=req.temperature,
                top_p=req.top_p,
                max_tokens=req.max_tokens,
            ):
                assistant_text += delta
                yield (
                    json.dumps({
                        "conversation_id": _conv_id,
                        "delta": delta,
                        "done": False,
                    })
                    + "\n"
                ).encode()

            # Append RAG citations to stream
            if citations:
                citation_md = "\n\n**Sources:**\n" + "\n".join(f"- {c}" for c in citations)
                assistant_text += citation_md
                yield (
                    json.dumps({
                        "conversation_id": _conv_id,
                        "delta": citation_md,
                        "done": False,
                    })
                    + "\n"
                ).encode()

            # ── Persist assistant reply in a fresh session ────────────────────
            _persist_assistant_message(_conv_id, assistant_text, model)

            # ── Auto-title: fire-and-forget via asyncio task ──────────────────
            if _is_new and _user_msg:
                asyncio.ensure_future(_background_title(_conv_id, _user_msg))

            # ── Done ─────────────────────────────────────────────────────────
            yield (
                json.dumps({"conversation_id": _conv_id, "delta": "", "done": True})
                + "\n"
            ).encode()

        except Exception as exc:
            logger.exception("Error in chat stream for conversation %d", _conv_id)
            err_msg = str(exc) or exc.__class__.__name__
            # Attempt to still persist whatever was generated
            if assistant_text:
                _persist_assistant_message(_conv_id, assistant_text, model)
            yield (
                json.dumps({
                    "conversation_id": _conv_id,
                    "delta": "",
                    "done": True,
                    "error": err_msg,
                })
                + "\n"
            ).encode()

    return StreamingResponse(_events(), media_type="application/x-ndjson")


def _persist_assistant_message(conversation_id: int, text: str, model: str) -> None:
    """Persist the assistant reply and bump updated_at in a fresh DB session."""
    db = SessionLocal()
    try:
        db.add(Message(
            conversation_id=conversation_id,
            role="assistant",
            content=text,
        ))
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            conv.model = model
            conv.updated_at = _utcnow()
            db.add(conv)
        db.commit()
    except Exception:
        logger.exception("Failed to persist assistant message for conversation %d", conversation_id)
    finally:
        db.close()


async def _background_title(conversation_id: int, user_message: str) -> None:
    """Generate and save auto-title without blocking the stream."""
    try:
        title = await auto_title(user_message)
        # DB update runs in threadpool
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _update_title_in_db, conversation_id, title)
    except Exception:
        logger.exception("Auto-title failed for conversation %d", conversation_id)


# ── Compat alias ──────────────────────────────────────────────────────────────

@router.post("/chat")
def chat_alias(req: schemas.ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Compatibility alias → same as POST /api/chat/stream."""
    return chat_stream(req=req, db=db, current_user=current_user)
