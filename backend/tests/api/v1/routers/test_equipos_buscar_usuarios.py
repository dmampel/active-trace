"""Tests de integración para GET /api/v1/equipos/usuarios/buscar.

TDD scenarios:
  - Coincidencias ILIKE → 200 con resultados
  - Sin coincidencias → 200 lista vacía
  - Sin permiso → 403
  - q < 2 chars → 422
"""
import uuid
import os
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from fastapi.testclient import TestClient

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


def _mock_usuario():
    from app.schemas.equipo import UsuarioBusquedaResponse
    return UsuarioBusquedaResponse(
        id=uuid.uuid4(),
        nombre="Juan",
        apellido="García",
        legajo="12345",
    )


# ── Sin permiso → 403 ─────────────────────────────────────────────────────────

def test_buscar_usuarios_no_permission_returns_403():
    """Sin permiso equipos:manage → 403."""
    with _client_with_perms(["equipos:read_own"]) as client:
        resp = client.get("/api/v1/equipos/usuarios/buscar?q=garcia")
    assert resp.status_code == 403


def test_buscar_usuarios_no_token_returns_401():
    """Sin token → 401."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/equipos/usuarios/buscar?q=garcia")
    assert resp.status_code == 401


# ── Coincidencias → 200 con resultados ───────────────────────────────────────

def test_buscar_usuarios_returns_coincidencias(monkeypatch):
    """GET ?q=garcia con permiso → 200 lista con resultados."""
    mock_result = [_mock_usuario()]
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "buscar_usuarios",
        AsyncMock(return_value=mock_result),
    )
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.get("/api/v1/equipos/usuarios/buscar?q=garcia")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["apellido"] == "García"


# ── Sin coincidencias → 200 [] ────────────────────────────────────────────────

def test_buscar_usuarios_sin_coincidencias_returns_empty(monkeypatch):
    """GET ?q=xyz sin resultados → 200 lista vacía."""
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "buscar_usuarios",
        AsyncMock(return_value=[]),
    )
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.get("/api/v1/equipos/usuarios/buscar?q=xyz")
    assert resp.status_code == 200
    assert resp.json() == []


# ── q < 2 chars → 422 ────────────────────────────────────────────────────────

def test_buscar_usuarios_q_too_short_returns_422():
    """GET ?q=x (1 char) → 422 Unprocessable Entity."""
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.get("/api/v1/equipos/usuarios/buscar?q=x")
    assert resp.status_code == 422


# ── limit > 50 → 422 ─────────────────────────────────────────────────────────

def test_buscar_usuarios_limit_too_large_returns_422():
    """GET ?limit=51 → 422 Unprocessable Entity."""
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.get("/api/v1/equipos/usuarios/buscar?q=garcia&limit=51")
    assert resp.status_code == 422
