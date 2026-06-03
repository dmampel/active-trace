import uuid
import pytest
from fastapi.testclient import TestClient
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from app.main import app
from app.core.dependencies import get_sync_db

app.dependency_overrides[get_sync_db] = lambda: None
client = TestClient(app)

def test_totp_enroll_requires_authentication():
    # Attempt to enroll without JWT
    tid = str(uuid.uuid4())
    headers = {
        "X-Tenant-ID": tid
    }
    
    response = client.post("/api/v1/auth/2fa/enroll", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_totp_enroll_confirm_requires_authentication():
    # Attempt to confirm enroll without JWT
    tid = str(uuid.uuid4())
    headers = {
        "X-Tenant-ID": tid
    }
    
    response = client.post("/api/v1/auth/2fa/enroll/confirm", headers=headers, json={"code": "123456"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
