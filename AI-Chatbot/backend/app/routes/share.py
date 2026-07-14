from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Conversation, Message, Share, User
from ..auth import get_current_user
from .. import schemas
import uuid

router = APIRouter(prefix="/api/share", tags=["share"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=schemas.ShareResponse)
def create_share(req: schemas.ShareCreateRequest, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == req.conversation_id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check if a share already exists
    share = db.query(Share).filter(Share.conversation_id == conv.id).first()
    if not share:
        share = Share(
            conversation_id=conv.id,
            is_public=req.is_public
        )
        db.add(share)
        db.commit()
        db.refresh(share)
    
    base_url = str(request.base_url).rstrip("/")
    share_url = f"{base_url}/share/{share.id}"
    
    return {"share_id": share.id, "share_url": share_url}


@router.get("/{share_id}", response_model=schemas.ShareViewResponse)
def view_share(share_id: str, db: Session = Depends(get_db)):
    share = db.query(Share).filter(Share.id == share_id).first()
    if not share or not share.is_public:
        raise HTTPException(status_code=404, detail="Share not found")
        
    conv = db.query(Conversation).filter(Conversation.id == share.conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    
    return {
        "share_id": share.id,
        "title": conv.title,
        "messages": [{"role": m.role, "content": m.content} for m in msgs]
    }
