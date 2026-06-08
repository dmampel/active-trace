import hashlib
import uuid
import pyotp
from datetime import timedelta
from fastapi.testclient import TestClient
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AES256GCMCipher, create_access_token, create_partial_token, hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.main import app

client = TestClient(app)

_CIPHER = AES256GCMCipher(hashlib.sha256(("b" * 64).encode()).digest())


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_tenant(db: AsyncSession) -> Tenant:
    t = Tenant(name=f"T-{uuid.uuid4().hex[:6]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def _make_user(db: AsyncSession, tenant_id: uuid.UUID, password: str = "pass123", **kwargs) -> User:
    u = User(
        tenant_id=tenant_id,
        email=f"u-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password(password),
        is_active=True,
        **kwargs,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


def _bearer(user: User) -> dict:
    token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id), "roles": []},
        timedelta(minutes=15),
    )
    return {"Authorization": f"Bearer {token}"}


# ── Sync TestClient tests (no DB) ─────────────────────────────────────────────

def test_totp_enroll_requires_authentication():
    tid = str(uuid.uuid4())
    response = client.post("/api/v1/auth/2fa/enroll", headers={"X-Tenant-ID": tid})
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_totp_enroll_confirm_requires_authentication():
    tid = str(uuid.uuid4())
    response = client.post(
        "/api/v1/auth/2fa/enroll/confirm",
        headers={"X-Tenant-ID": tid},
        json={"code": "123456"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_invalid_tenant_id_returns_400():
    response = client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": "not-a-uuid"},
        json={"email": "a@b.com", "password": "pass"},
    )
    assert response.status_code == 400
    assert "Invalid tenant ID" in response.json()["detail"]


# ── Async HTTP tests (with DB via app_client + db_session) ────────────────────

async def test_login_success_returns_tokens(app_client, db_session: AsyncSession):
    tenant = await _make_tenant(db_session)
    user = await _make_user(db_session, tenant.id, password="mypass123")

    resp = await app_client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"email": user.email, "password": "mypass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_bad_credentials_returns_401(app_client, db_session: AsyncSession):
    tenant = await _make_tenant(db_session)

    resp = await app_client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"email": "nobody@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_refresh_returns_new_tokens(app_client, db_session: AsyncSession):
    tenant = await _make_tenant(db_session)
    user = await _make_user(db_session, tenant.id, password="mypass123")

    login_resp = await app_client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"email": user.email, "password": "mypass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await app_client.post(
        "/api/v1/auth/refresh",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_refresh_bad_token_returns_401(app_client, db_session: AsyncSession):
    tenant = await _make_tenant(db_session)

    resp = await app_client.post(
        "/api/v1/auth/refresh",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"refresh_token": "bad_token_xyz"},
    )
    assert resp.status_code == 401


async def test_logout_returns_204(app_client, db_session: AsyncSession):
    tenant = await _make_tenant(db_session)
    user = await _make_user(db_session, tenant.id, password="mypass123")

    login_resp = await app_client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"email": user.email, "password": "mypass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await app_client.post(
        "/api/v1/auth/logout",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 204


async def test_forgot_password_returns_200(app_client, db_session: AsyncSession):
    tenant = await _make_tenant(db_session)

    resp = await app_client.post(
        "/api/v1/auth/forgot-password",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"email": "ghost@example.com"},
    )
    assert resp.status_code == 200


async def test_reset_password_bad_token_returns_400(app_client, db_session: AsyncSession):
    tenant = await _make_tenant(db_session)

    resp = await app_client.post(
        "/api/v1/auth/reset-password",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"token": "bad_token_xyz", "new_password": "new_secure_pass_123"},
    )
    assert resp.status_code == 400


async def test_totp_confirm_endpoint_success(app_client, db_session: AsyncSession):
    secret = pyotp.random_base32()
    tenant = await _make_tenant(db_session)
    user = await _make_user(
        db_session,
        tenant.id,
        totp_enabled=True,
        totp_secret_enc=_CIPHER.encrypt(secret),
    )
    partial_token = create_partial_token(str(user.id), str(tenant.id))
    code = pyotp.TOTP(secret).now()

    resp = await app_client.post(
        "/api/v1/auth/2fa/confirm",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"partial_token": partial_token, "code": code},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


async def test_totp_confirm_bad_code_returns_401(app_client, db_session: AsyncSession):
    secret = pyotp.random_base32()
    tenant = await _make_tenant(db_session)
    user = await _make_user(
        db_session,
        tenant.id,
        totp_enabled=True,
        totp_secret_enc=_CIPHER.encrypt(secret),
    )
    partial_token = create_partial_token(str(user.id), str(tenant.id))

    resp = await app_client.post(
        "/api/v1/auth/2fa/confirm",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"partial_token": partial_token, "code": "000000"},
    )
    assert resp.status_code == 401


async def test_totp_enroll_authenticated(app_client, db_session: AsyncSession):
    tenant = await _make_tenant(db_session)
    user = await _make_user(db_session, tenant.id)

    resp = await app_client.post(
        "/api/v1/auth/2fa/enroll",
        headers=_bearer(user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "otpauth_uri" in data
    assert "qr_base64" in data


async def test_totp_enroll_confirm_authenticated(app_client, db_session: AsyncSession):
    secret = pyotp.random_base32()
    tenant = await _make_tenant(db_session)
    user = await _make_user(
        db_session,
        tenant.id,
        totp_pending_secret_enc=_CIPHER.encrypt(secret),
    )
    code = pyotp.TOTP(secret).now()

    resp = await app_client.post(
        "/api/v1/auth/2fa/enroll/confirm",
        headers=_bearer(user),
        json={"code": code},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "TOTP successfully enrolled"
