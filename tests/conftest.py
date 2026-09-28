import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bilimai.db")
os.environ.setdefault("AI_API_KEY", "")
os.environ.setdefault("SECRET_KEY", "test-secret-key-please-change-32-chars-xxx")

import pytest
from fastapi.testclient import TestClient

from app.database import init_db, engine, Base
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
