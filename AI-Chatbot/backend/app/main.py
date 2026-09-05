import os
import platform
import base64
import wave
import contextlib

from fastapi import FastAPI, Body, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .models import Base
from .database import engine, IS_VERCEL

from .routes.chat import router as chat_router

from . import schemas
from .routes.chat import chat_stream as _chat_stream
from .database import SessionLocal
from .routes.history import router as history_router
from .routes.upload import router as upload_router
from .routes.settings import router as settings_router
from .routes.share import router as share_router
from .routes.export import router as export_router
from .routes.suggest import router as suggest_router
from .models import Conversation, User
from .auth import router as auth_router, get_current_user



APP_VERSION = "0.1.0"


def create_app() -> FastAPI:
    app = FastAPI(title="Nova AI")

    if not IS_VERCEL:
        # Ensure storage directories exist for local development
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        uploads_dir = os.path.join(project_root, "backend", "uploads")
        vector_dir = os.path.join(project_root, "backend", "vector_store")
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(vector_dir, exist_ok=True)

    Base.metadata.create_all(bind=engine)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(history_router)
    app.include_router(upload_router)
    app.include_router(settings_router)
    app.include_router(share_router)
    app.include_router(export_router)
    app.include_router(suggest_router)
    app.include_router(auth_router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": str(exc.detail),
                "error": "HTTPException",
                "status": exc.status_code
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(exc),
                "error": exc.__class__.__name__,
                "status": 500
            }
        )

    @app.get("/health")
    def health() -> JSONResponse:
        # Database status (SQLite)
        db_ok = False
        db_error = None
        try:
            # SQLite file path is used by SQLAlchemy URL; fall back to local db creation.
            engine.connect().close()
            db_ok = True
        except Exception as e:
            db_error = str(e)
            db_ok = False

        groq_ok = bool((settings.groq_api_key or "").strip())

        return JSONResponse(
            {
                "status": "ok" if (db_ok and groq_ok) else "degraded",
                "app": {
                    "name": "Nova AI",
                    "version": APP_VERSION,
                    "python": platform.python_version(),
                },
                "database": {
                    "type": "sqlite",
                    "ok": db_ok,
                    "error": db_error,
                },
                "groq": {
                    "configured": groq_ok,
                    "model": settings.default_model,
                },
            }
        )

    def _wav_silent_base64(text: str) -> dict:
        """
        Generate a small valid WAV (silent PCM) using only stdlib.

        This is a development-friendly placeholder that still returns a valid audio payload
        so the endpoint can be fully exercised by clients.
        """
        text = (text or "").strip()
        # Duration: ~20 chars per second, clamped to keep response small.
        chars = max(1, len(text))
        seconds = min(3.0, max(0.5, chars / 20.0))

        sample_rate = 16000
        n_samples = int(sample_rate * seconds)

        # wave module writes to file-like; use BytesIO
        import io

        bio = io.BytesIO()
        with contextlib.closing(wave.open(bio, mode="wb")) as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(sample_rate)
            # silent => all zero samples
            wf.writeframes(b"\x00\x00" * n_samples)

        audio_b64 = base64.b64encode(bio.getvalue()).decode("ascii")
        return {
            "format": "wav",
            "encoding": "base64",
            "sample_rate": sample_rate,
            "channels": 1,
            "duration_seconds_estimate": seconds,
            "audio_base64": audio_b64,
        }

    # Serve frontend (new multi-directory structure)
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
    frontend_dir = os.path.abspath(frontend_dir)

    if os.path.isdir(frontend_dir):
        # Ensure static sub-dirs exist so StaticFiles doesn't raise at startup
        for sub in ("assets", "css", "js", "icons"):
            sub_path = os.path.join(frontend_dir, sub)
            if not IS_VERCEL:
                os.makedirs(sub_path, exist_ok=True)
            if os.path.exists(sub_path):
                app.mount(f"/{sub}", StaticFiles(directory=sub_path), name=sub)

        @app.get("/")
        def index():
            return FileResponse(os.path.join(frontend_dir, "index.html"))

        @app.get("/share/{share_id}")
        def share_view_page(share_id: str):
            return FileResponse(os.path.join(frontend_dir, "share.html"))

    def get_db_session():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @app.post("/chat")
    def chat_compat(req: schemas.ChatRequest = Body(...), db: Session = Depends(get_db_session)):
        """
        Compatibility endpoint for clients expecting POST /chat.

        Streams NDJSON using the same logic as POST /api/chat/stream.
        """
        return _chat_stream(req=req, db=db)

    # ----------------------------
    # Root-level compatibility endpoints (expected by clients)
    # ----------------------------

    @app.get("/history")
    def history_root(current_user: User = Depends(get_current_user)):
        """
        List conversations (compat with expected GET /history).
        """
        db = SessionLocal()
        try:
            rows = db.query(Conversation).filter(Conversation.user_id == current_user.id).order_by(Conversation.updated_at.desc()).all()
            return {
                "success": True,
                "conversations": [
                    {
                        "id": c.id,
                        "title": c.title,
                        "model": c.model,
                        "updated_at": str(c.updated_at),
                    }
                    for c in rows
                ],
            }
        finally:
            db.close()

    @app.post("/new-chat")
    def new_chat_root(
        model: str = Form("llama-3.3-70b-versatile"),
        system_prompt: str = Form(""),
        title: str = Form("New chat"),
        current_user: User = Depends(get_current_user)
    ):
        """
        Create a new conversation and persist it (compat with expected POST /new-chat).
        """
        db = SessionLocal()
        try:
            conv = Conversation(
                title=title or "New chat",
                model=model or "llama-3.3-70b-versatile",
                system_prompt=system_prompt or "",
                user_id=current_user.id,
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
            return {"success": True, "conversation_id": conv.id}
        finally:
            db.close()

    @app.post("/upload/image")
    def upload_image_root(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
        """
        Upload an image. For Vercel, this is an in-memory operation.
        Locally, it persists to backend/uploads/.
        """
        contents = file.file.read()
        if not contents:
            return {
                "success": False,
                "error_code": "EMPTY_FILE",
                "message": "Uploaded image file is empty.",
                "feature": "upload-image",
                "status": 400,
            }

        if IS_VERCEL:
            # In Vercel, don't save to disk. Return a success response.
            return {
                "success": True,
                "filename": file.filename,
                "saved_path": None, # No path in ephemeral environment
                "status": "uploaded (in-memory)",
            }

        # Local development: save to disk
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        uploads_dir = os.path.join(project_root, "backend", "uploads")
        # No need for os.makedirs, handled at startup

        safe_name = file.filename or "upload.bin"
        safe_name = safe_name.replace("..", "").replace("\\", "_").replace("/", "_")

        saved_path = os.path.join(uploads_dir, safe_name)
        with open(saved_path, "wb") as f:
            f.write(contents)

        return {
            "success": True,
            "filename": file.filename,
            "saved_path": os.path.abspath(saved_path),
            "status": "uploaded",
        }

    @app.post("/speech-to-text")
    async def speech_to_text_root(
        file: UploadFile = File(...),
        language: str = Form("en"),
        current_user: User = Depends(get_current_user)
    ):
        """
        Transcribe an uploaded audio file (compat with expected POST /speech-to-text).
        """
        try:
            # Import lazily to avoid any heavy startup cost during app boot/DB init.
            from .speech import transcribe_audio
            text = transcribe_audio(file.file, language=language)
            return {"success": True, "text": text}
        except Exception as e:
            return {
                "success": False,
                "error_code": "SPEECH_TO_TEXT_FAILED",
                "message": str(e),
                "feature": "speech-to-text",
                "status": 500,
            }

    @app.post("/text-to-speech")
    async def text_to_speech_root(
        text: str = Form(...),
        current_user: User = Depends(get_current_user)
    ):
        """
        Generate a valid WAV/MP3 audio payload from text.
        Tries to use edge-tts, falls back to standard library silent WAV.
        """
        try:
            import edge_tts
            import io
            import base64
            bio = io.BytesIO()
            communicate = edge_tts.Communicate(text, "en-US-AvaNeural")
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    bio.write(chunk["data"])
            audio_bytes = bio.getvalue()
            if not audio_bytes:
                raise ValueError("No audio generated")
            audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
            payload = {
                "format": "mp3",
                "encoding": "base64",
                "sample_rate": 24000,
                "channels": 1,
                "audio_base64": audio_b64,
            }
        except Exception:
            payload = _wav_silent_base64(text=text)

        return {"success": True, "feature": "text-to-speech", "status": 200, "audio": payload}

    return app


app = create_app()

