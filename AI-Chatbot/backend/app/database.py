import os
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

IS_VERCEL = os.environ.get("VERCEL") == "1"

if IS_VERCEL:
    # Use a shared in-memory SQLite database for Vercel's ephemeral environment.
    # The database will exist only for the duration of the function invocation.
    DATABASE_URL = "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    # Use a file-based SQLite database for local development.
    db_path = "chatbot.db"
    DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

