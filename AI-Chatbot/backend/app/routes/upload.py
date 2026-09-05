import os
import base64
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from ..rag import process_pdf
from ..database import SessionLocal
from ..models import Conversation, User, ImageAttachment
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
    conversation_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and index a PDF for RAG. Auto-creates conversation if not supplied.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # If conversation_id is missing or doesn't exist, create one
    conv = None
    if conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()

    if not conv:
        clean_title = f"Doc: {file.filename[:30]}"
        conv = Conversation(
            title=clean_title,
            user_id=current_user.id
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    try:
        contents = file.file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="PDF file is empty")

        num_chunks = process_pdf(
            file_contents=contents,
            filename=file.filename,
            conversation_id=conv.id,
            db=db
        )

        return {
            "success": True,
            "filename": file.filename,
            "conversation_id": conv.id,
            "chunks": num_chunks,
            "status": "processed",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index PDF: {str(e)}")


@router.post("/image")
def upload_image(
    conversation_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an image for analysis. Returns base64 data_url for instant rendering and AI vision.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    mime_type = file.content_type or "image/png"
    b64_str = base64.b64encode(contents).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64_str}"

    conv = None
    if conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()

    # Save attachment record
    img = ImageAttachment(
        conversation_id=conv.id if conv else None,
        filename=file.filename,
        mime_type=mime_type,
        data_base64=b64_str,
    )
    db.add(img)
    db.commit()
    db.refresh(img)

    return {
        "success": True,
        "filename": file.filename,
        "attachment_id": img.id,
        "conversation_id": conv.id if conv else None,
        "data_url": data_url,
        "preview_url": data_url,
        "status": "uploaded",
    }
