"""Tests de integración para el router de usuarios.

Tasks 5.4, 5.5:
  5.4 - CRUD completo: crear → listar (sin PII) → detalle (con PII) → editar → soft delete
  5.5 - Sin permiso → 403; sin token → 401; usuario otro tenant → 404; email duplicado → 409
"""
import uuid
import os
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from app.main import app
from app.core.dependencies import get_current_user, get_db

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


def _make_user():
    user = MagicMock()
    user.id = USER_ID
    user.tenant_id = TENANT_ID
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


@contextmanager
def _client_with_perms(perms: list[str]):
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_db] = _fake_db
    target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(target, new=AsyncMock(return_value=set(perms))):
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def _mock_usuario_list_item():
    from app.schemas.usuario import UsuarioListItem
    from app.models.estructura import EstadoEntidad
    return UsuarioListItem(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        email="test@example.com",
        facturador=False,
        estado=EstadoEntidad.activa,
    )


def _mock_usuario_detail():
    from app.schemas.usuario import UsuarioDetail
    from app.models.estructura import EstadoEntidad
    return UsuarioDetail(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        email="test@example.com",
        dni="12345678",
        facturador=False,
        estado=EstadoEntidad.activa,
    )


# ── 5.5 Sin token → 401 ───────────────────────────────────────────────────────

def test_get_usuarios_no_token_returns_401():
    """Sin token → 401."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/usuarios")
    assert resp.status_code == 401


# ── 5.5 Sin permiso → 403 ─────────────────────────────────────────────────────

def test_get_usuarios_no_permission_returns_403():
    """Sin permiso usuarios:gestionar → 403."""
    with _client_with_perms([]) as client:
        resp = client.get("/api/v1/usuarios")
    assert resp.status_code == 403


# ── 5.4 POST /usuarios → 201 ─────────────────────────────────────────────────

def test_post_usuario_returns_201(monkeypatch):
    """POST con permiso y datos válidos → 201."""
    mock_item = _mock_usuario_list_item()
    from app.services import usuario_service as svc_mod
    monkeypatch.setattr(
        svc_mod.UsuarioService, "create",
        AsyncMock(return_value=mock_item),
    )
    with _client_with_perms(["usuarios:gestionar"]) as client:
        resp = client.post(
            "/api/v1/usuarios",
            json={"email": "test@example.com", "password": "secret"},
        )
    assert resp.status_code == 201


# ── 5.4 POST /usuarios email duplicado → 409 ─────────────────────────────────

def test_post_usuario_duplicate_email_returns_409(monkeypatch):
    """Email duplicado en mismo tenant → 409."""
    from app.services import usuario_service as svc_mod
    monkeypatch.setattr(
        svc_mod.UsuarioService, "create",
        AsyncMock(side_effect=HTTPException(status_code=409, detail="Email ya registrado en el tenant")),
    )
    with _client_with_perms(["usuarios:gestionar"]) as client:
        resp = client.post(
            "/api/v1/usuarios",
            json={"email": "dup@example.com", "password": "secret"},
        )
    assert resp.status_code == 409


# ── 5.4 GET /usuarios → 200 lista sin PII ─────────────────────────────────────

def test_get_usuarios_returns_list_without_pii(monkeypatch):
    """GET listado → 200 y no expone campos PII."""
    mock_item = _mock_usuario_list_item()
    from app.services import usuario_service as svc_mod
    monkeypatch.setattr(
        svc_mod.UsuarioService, "list_users",
        AsyncMock(return_value=[mock_item]),
    )
    with _client_with_perms(["usuarios:gestionar"]) as client:
        resp = client.get("/api/v1/usuarios")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for pii_field in ("dni", "cuil", "cbu", "alias_cbu"):
        assert pii_field not in data[0], f"Campo PII {pii_field} no debe aparecer en listado"


# ── 5.4 GET /usuarios/{id} → 200 detalle con PII ─────────────────────────────

def test_get_usuario_detail_returns_pii(monkeypatch):
    """GET detalle → 200 con campos PII."""
    mock_detail = _mock_usuario_detail()
    from app.services import usuario_service as svc_mod
    monkeypatch.setattr(
        svc_mod.UsuarioService, "get_detail",
        AsyncMock(return_value=mock_detail),
    )
    uid = uuid.uuid4()
    with _client_with_perms(["usuarios:gestionar"]) as client:
        resp = client.get(f"/api/v1/usuarios/{uid}")
    assert resp.status_code == 200
    data = resp.json()
    assert "dni" in data


# ── 5.5 GET otro tenant → 404 ────────────────────────────────────────────────

def test_get_usuario_other_tenant_returns_404(monkeypatch):
    """Usuario de otro tenant → 404 (el service lanza 404)."""
    from app.services import usuario_service as svc_mod
    monkeypatch.setattr(
        svc_mod.UsuarioService, "get_detail",
        AsyncMock(side_effect=HTTPException(status_code=404, detail="Usuario no encontrado")),
    )
    uid = uuid.uuid4()
    with _client_with_perms(["usuarios:gestionar"]) as client:
        resp = client.get(f"/api/v1/usuarios/{uid}")
    assert resp.status_code == 404


# ── 5.4 PATCH /usuarios/{id} → 200 ──────────────────────────────────────────

def test_patch_usuario_returns_200(monkeypatch):
    """PATCH con datos válidos → 200."""
    mock_item = _mock_usuario_list_item()
    from app.services import usuario_service as svc_mod
    monkeypatch.setattr(
        svc_mod.UsuarioService, "update",
        AsyncMock(return_value=mock_item),
    )
    uid = uuid.uuid4()
    with _client_with_perms(["usuarios:gestionar"]) as client:
        resp = client.patch(f"/api/v1/usuarios/{uid}", json={"nombre": "Nuevo"})
    assert resp.status_code == 200


# ── 5.4 DELETE /usuarios/{id} → 204 ─────────────────────────────────────────

def test_delete_usuario_returns_204(monkeypatch):
    """DELETE → 204."""
    from app.services import usuario_service as svc_mod
    monkeypatch.setattr(
        svc_mod.UsuarioService, "soft_delete",
        AsyncMock(return_value=None),
    )
    uid = uuid.uuid4()
    with _client_with_perms(["usuarios:gestionar"]) as client:
        resp = client.delete(f"/api/v1/usuarios/{uid}")
    assert resp.status_code == 204
