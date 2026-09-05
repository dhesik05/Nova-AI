import jwt
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests

from . import schemas, models
from .database import SessionLocal
from .config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> models.User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/login", response_model=schemas.Token)
def login_with_name(req: schemas.NameLoginRequest, db: Session = Depends(get_db)):
    """
    Direct Name Login: Anyone can enter their name to start chatting immediately.
    """
    clean_name = (req.name or "").strip()
    if not clean_name:
        clean_name = "Nova User"
    
    # Check if a user with this name already exists or create one
    user = db.query(models.User).filter(models.User.name == clean_name).first()
    
    if not user:
        user_id_str = f"usr-{uuid.uuid4().hex[:10]}"
        user = models.User(
            google_id=user_id_str,
            email=f"{clean_name.lower().replace(' ', '_')}@nova.local",
            name=clean_name,
            profile_picture=""
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.post("/google", response_model=schemas.Token)
def google_auth(req: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        if settings.google_client_id:
            idinfo = id_token.verify_oauth2_token(req.credential, requests.Request(), settings.google_client_id)
        else:
            # If no client ID configured on backend, just decode without verification for dev mode.
            # WARNING: NOT FOR PRODUCTION
            idinfo = jwt.decode(req.credential, options={"verify_signature": False})
            
        if idinfo.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")
            
        google_id = idinfo["sub"]
        email = idinfo.get("email", "")
        name = idinfo.get("name", "")
        picture = idinfo.get("picture", "")

        user = db.query(models.User).filter(models.User.google_id == google_id).first()
        
        if not user:
            user = models.User(
                google_id=google_id,
                email=email,
                name=name,
                profile_picture=picture
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            user.name = name
            user.profile_picture = picture
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": user.id})
        return {"access_token": access_token, "token_type": "bearer", "user": user}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.post("/guest", response_model=schemas.Token)
def guest_auth(db: Session = Depends(get_db)):
    guest_id = f"guest-{uuid.uuid4()}"
    
    user = models.User(
        google_id=guest_id,
        email=f"{guest_id}@guest.local",
        name="Guest User",
        profile_picture="https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer", "user": user}
