import io
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Conversation, Message, User
from ..auth import get_current_user

router = APIRouter(prefix="/api/export", tags=["export"])
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/pdf/{conversation_id}")
def export_pdf(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    # Try fpdf2 first; fall back to plain-text if not installed
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, f"Nova AI Chat - {conv.title}", ln=True)
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 10, f"Model: {conv.model}", ln=True)
        pdf.ln(5)

        for msg in msgs:
            role = "User" if msg.role == "user" else "Assistant"
            pdf.set_font("helvetica", "B", 11)
            pdf.cell(0, 6, f"{role}:", ln=True)
            pdf.set_font("helvetica", "", 10)
            text_safe = (msg.content or "").encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, text_safe)
            pdf.ln(4)

        pdf_bytes = pdf.output()
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=chat_{conversation_id}.pdf"},
        )

    except ImportError:
        logger.warning("fpdf not installed — falling back to text/plain PDF export")
        # Fall through to text export as plain attachment
        output = _build_txt(conv, msgs)
        return StreamingResponse(
            io.BytesIO(output.encode("utf-8")),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=chat_{conversation_id}.txt"},
        )
    except Exception as e:
        logger.exception("PDF export failed for conversation %d", conversation_id)
        raise HTTPException(status_code=500, detail=f"PDF export failed: {e}")


@router.get("/txt/{conversation_id}")
def export_txt(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    output = _build_txt(conv, msgs)
    return StreamingResponse(
        io.BytesIO(output.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=chat_{conversation_id}.txt"},
    )


def _build_txt(conv, msgs) -> str:
    output = f"Nova AI Chat - {conv.title}\n"
    output += f"Model: {conv.model}\n"
    output += "=" * 40 + "\n\n"
    for msg in msgs:
        role = "USER" if msg.role == "user" else "ASSISTANT"
        output += f"[{role}]:\n{msg.content or ''}\n\n"
    return output
