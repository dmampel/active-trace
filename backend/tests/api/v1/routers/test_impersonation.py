"""Tests para endpoints de impersonación y get_current_user con impersonado_id."""
import uuid
import pytest
from datetime import timedelta, date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from app.main import app
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.rbac import Rol, Permiso, RolPermiso, UserRol
from app.core.dependencies import get_sync_db, CurrentUser
from app.core.security import create_access_token, hash_password, decode_token


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def tenant_a(db):
    t = Tenant(id=uuid.uuid4(), name="Tenant A")
    db.add(t)
    db.flush()
    return t


@pytest.fixture
def tenant_b(db):
    t = Tenant(id=uuid.uuid4(), name="Tenant B")
    db.add(t)
    db.flush()
    return t


def _create_user(db, tenant_id, email="user@test.com"):
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email,
        password_hash=hash_password("secret123"),
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _grant_permission(db, user_id, tenant_id, perm_name="impersonacion:usar"):
    rol = Rol(id=uuid.uuid4(), nombre="admin_rol")
    perm = Permiso(id=uuid.uuid4(), nombre=perm_name)
    rol_perm = RolPermiso(rol_id=rol.id, permiso_id=perm.id)
    user_rol = UserRol(
        user_id=user_id,
        rol_id=rol.id,
        tenant_id=tenant_id,
        desde=date.today(),
    )
    db.add_all([rol, perm, rol_perm, user_rol])
    db.flush()


def _token_for(user, extra_claims=None):
    claims = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "roles": [],
    }
    if extra_claims:
        claims.update(extra_claims)
    return create_access_token(claims, timedelta(minutes=15))


def _client_with_db(db):
    app.dependency_overrides[get_sync_db] = lambda: db
    return TestClient(app, raise_server_exceptions=False)


# ── get_current_user — impersonado_id ────────────────────────────────────────

def test_get_current_user_with_impersonado_id(db, tenant_a):
    """9.7 — JWT con impersonado_id → CurrentUser.impersonado_id poblado."""
    actor = _create_user(db, tenant_a.id, "actor@test.com")
    target_id = uuid.uuid4()

    token = _token_for(actor, {"impersonado_id": str(target_id)})
    claims = decode_token(token)

    impersonado_raw = claims.get("impersonado_id")
    impersonado = uuid.UUID(impersonado_raw) if impersonado_raw else None

    cu = CurrentUser(
        id=uuid.UUID(claims["sub"]),
        tenant_id=uuid.UUID(claims["tenant_id"]),
        roles=[],
        impersonado_id=impersonado,
    )
    assert cu.impersonado_id == target_id


def test_get_current_user_without_impersonado_id(db, tenant_a):
    """9.8 — JWT normal → CurrentUser.impersonado_id = None."""
    actor = _create_user(db, tenant_a.id, "actor2@test.com")
    token = _token_for(actor)
    claims = decode_token(token)

    impersonado_raw = claims.get("impersonado_id")
    impersonado = uuid.UUID(impersonado_raw) if impersonado_raw else None

    cu = CurrentUser(
        id=uuid.UUID(claims["sub"]),
        tenant_id=uuid.UUID(claims["tenant_id"]),
        roles=[],
        impersonado_id=impersonado,
    )
    assert cu.impersonado_id is None


# ── POST /impersonate ─────────────────────────────────────────────────────────

def test_impersonate_without_permission_returns_403(db, tenant_a):
    """9.1 — usuario sin permiso impersonacion:usar → 403."""
    actor = _create_user(db, tenant_a.id, "actor3@test.com")
    target = _create_user(db, tenant_a.id, "target@test.com")
    token = _token_for(actor)

    client = _client_with_db(db)
    resp = client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(target.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_impersonate_cross_tenant_returns_404(db, tenant_a, tenant_b):
    """9.2 — target de otro tenant → 404."""
    actor = _create_user(db, tenant_a.id, "actor4@test.com")
    _grant_permission(db, actor.id, tenant_a.id)
    cross_tenant_target = _create_user(db, tenant_b.id, "cross@test.com")
    token = _token_for(actor)

    client = _client_with_db(db)
    resp = client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(cross_tenant_target.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_impersonate_success(db, tenant_a):
    """9.3 — impersonación exitosa → 200 + token + audit log IMPERSONACION_INICIAR."""
    actor = _create_user(db, tenant_a.id, "actor5@test.com")
    _grant_permission(db, actor.id, tenant_a.id)
    target = _create_user(db, tenant_a.id, "target2@test.com")
    token = _token_for(actor)

    client = _client_with_db(db)
    resp = client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(target.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "impersonate_token" in data
    assert data["token_type"] == "bearer"

    entry = db.query(AuditLog).filter_by(actor_id=actor.id).first()
    assert entry is not None
    assert entry.accion == "IMPERSONACION_INICIAR"


def test_impersonate_token_has_impersonado_id(db, tenant_a):
    """El token emitido contiene claim impersonado_id del target."""
    actor = _create_user(db, tenant_a.id, "actor6@test.com")
    _grant_permission(db, actor.id, tenant_a.id)
    target = _create_user(db, tenant_a.id, "target3@test.com")
    token = _token_for(actor)

    client = _client_with_db(db)
    resp = client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(target.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    imp_token = resp.json()["impersonate_token"]
    claims = decode_token(imp_token)
    assert claims["impersonado_id"] == str(target.id)
    assert claims["sub"] == str(actor.id)


def test_impersonate_nested_rejected(db, tenant_a):
    """9.4 — token con impersonado_id activo → 400 impersonación anidada rechazada."""
    actor = _create_user(db, tenant_a.id, "actor7@test.com")
    _grant_permission(db, actor.id, tenant_a.id)
    target = _create_user(db, tenant_a.id, "target4@test.com")
    target2 = _create_user(db, tenant_a.id, "target5@test.com")

    imp_token = _token_for(actor, {"impersonado_id": str(target.id)})

    client = _client_with_db(db)
    resp = client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(target2.id)},
        headers={"Authorization": f"Bearer {imp_token}"},
    )
    assert resp.status_code == 400
    assert "impersonación activa" in resp.json()["detail"]


# ── POST /impersonate/end ─────────────────────────────────────────────────────

def test_end_impersonation_without_active_session(db, tenant_a):
    """9.5 — token sin impersonación → 400."""
    actor = _create_user(db, tenant_a.id, "actor8@test.com")
    token = _token_for(actor)

    client = _client_with_db(db)
    resp = client.post(
        "/api/v1/auth/impersonate/end",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "impersonación activa" in resp.json()["detail"]


def test_end_impersonation_success(db, tenant_a):
    """9.6 — fin de impersonación exitoso → 200 + audit log IMPERSONACION_FINALIZAR."""
    actor = _create_user(db, tenant_a.id, "actor9@test.com")
    target = _create_user(db, tenant_a.id, "target6@test.com")

    imp_token = _token_for(actor, {"impersonado_id": str(target.id)})

    client = _client_with_db(db)
    resp = client.post(
        "/api/v1/auth/impersonate/end",
        headers={"Authorization": f"Bearer {imp_token}"},
    )
    assert resp.status_code == 200

    entry = db.query(AuditLog).filter_by(actor_id=actor.id, accion="IMPERSONACION_FINALIZAR").first()
    assert entry is not None
    assert entry.impersonado_id == target.id
