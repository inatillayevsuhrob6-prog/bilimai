"""Database engine, session and base declarative model."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.config import settings

url = settings.database_url_normalized

# SQLite uchun check_same_thread kerak; PostgreSQL uchun yo'q
connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}

engine = create_engine(
    url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables."""
    from app.models import (  # noqa: F401
        user, subject, lesson, question, answer, test_result,
        note, learning_history, achievement, notification,
        user_settings, audit_log, ai_conversation,
    )
    Base.metadata.create_all(bind=engine)
