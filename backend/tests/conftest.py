import os, sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

os.environ["DATABASE_URL"] = "mysql+pymysql://test:test@database.invalid:3306/dms_test"
os.environ.update(
    CORS_ORIGINS="http://127.0.0.1:5500,http://localhost:5500",
    COOKIE_SECURE="false",
    SESSION_HOURS="8",
    DB_TIME_ZONE="+05:30",
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

ADMIN = {
    "user_id": 1,
    "full_name": "Test Administrator",
    "email": "admin@example.test",
    "role": "ADMIN",
    "status": "ACTIVE",
}
PUBLIC = {**ADMIN, "user_id": 2, "role": "PUBLIC_USER"}


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def client(db):
    def isolated_db():
        try:
            yield db
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = isolated_db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()
