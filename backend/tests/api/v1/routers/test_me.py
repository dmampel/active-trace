import uuid
import pytest
import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from app.main import app
from app.core.security import create_access_token
from app.core.dependencies import get_sync_db
from datetime import timedelta
from fastapi.testclient import TestClient

app.dependency_overrides[get_sync_db] = lambda: None
client = TestClient(app)

@pytest.fixture
def auth_headers():
    def _get_headers(tenant_id: str, user_id: str, roles: list[str]):
        token = create_access_token(
            {"sub": user_id, "tenant_id": tenant_id, "roles": roles},
            timedelta(minutes=15)
        )
        return {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": tenant_id
        }
    return _get_headers

def test_get_me(auth_headers):
    uid = str(uuid.uuid4())
    tid = str(uuid.uuid4())
    headers = auth_headers(tid, uid, ["ADMIN"])
    
    response = client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == uid
    assert response.json()["tenant_id"] == tid
    assert "ADMIN" in response.json()["roles"]

def test_protected_endpoint_without_permission_returns_403(auth_headers, monkeypatch):
    uid = str(uuid.uuid4())
    tid = str(uuid.uuid4())
    headers = auth_headers(tid, uid, ["ALUMNO"])

    # Mock get_effective_permissions to return something else
    def mock_get_perms(session, user_id, tenant_id):
        return {"otro:permiso"}
    
    monkeypatch.setattr("app.core.permissions.RbacRepository.get_effective_permissions", mock_get_perms)

    response = client.get("/api/v1/me/protected", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden: missing permission auditoria:ver"

def test_protected_endpoint_with_permission_returns_200(auth_headers, monkeypatch):
    uid = str(uuid.uuid4())
    tid = str(uuid.uuid4())
    headers = auth_headers(tid, uid, ["ADMIN"])

    def mock_get_perms(session, user_id, tenant_id):
        return {"auditoria:ver"}
    
    monkeypatch.setattr("app.core.permissions.RbacRepository.get_effective_permissions", mock_get_perms)

    response = client.get("/api/v1/me/protected", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "You have access to auditoria:ver"
