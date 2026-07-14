import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from ..rag import process_pdf
from ..database import SessionLocal
from ..models import Conversation, User
from ..auth import get_current_user

router = APIRouter(prefix="/api/upload", tags=["upload"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/pdf")
def upload_pdf(
    conversation_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        contents = file.file.read()
        num_chunks = process_pdf(
            file_contents=contents,
            filename=file.filename,
            conversation_id=conversation_id
        )
        return {
            "success": True,
            "filename": file.filename,
            "chunks": num_chunks,
            "status": "processed",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index PDF: {str(e)}")

