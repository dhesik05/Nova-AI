import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set env before importing app
os.environ["GROQ_API_KEY"] = "test_key"
os.environ["IS_VERCEL"] = "1"

from backend.app.main import app
from backend.app.models import Base
from backend.app.auth import get_current_user
from backend.app.models import User
from backend.app.routes.chat import get_db as get_chat_db

# Setup in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_get_current_user():
    return User(
        id=1,
        google_id="12345",
        email="test@example.com",
        name="Test User",
        profile_picture="http://example.com/pic.jpg",
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc)
    )

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client():
    app.dependency_overrides[get_current_user] = override_get_current_user
    # Some routers have their own get_db or similar depending on how they are imported
    # Override the ones we know about
    app.dependency_overrides[get_chat_db] = override_get_db
    
    # Also override for auth module if needed
    from backend.app.auth import get_db as get_auth_db
    app.dependency_overrides[get_auth_db] = override_get_db

    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()
