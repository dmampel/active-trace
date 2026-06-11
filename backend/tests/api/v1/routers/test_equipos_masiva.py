"""Tests de integración para POST /api/v1/equipos/masiva.

TDD scenarios:
  - Creación exitosa → 201 con { "creadas": N }
  - Contexto otro tenant → 422 (lanzado por service)
  - lista vacía de usuario_ids → 422
  - Sin permiso → 403
"""
import uuid
import os
from contextlib import contextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

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


def _valid_body():
    return {
        "usuario_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        "cohorte_id": str(uuid.uuid4()),
        "rol": "PROFESOR",
        "desde": str(date.today()),
    }


# ── Sin permiso → 403 ─────────────────────────────────────────────────────────

def test_masiva_no_permission_returns_403():
    """Sin permiso equipos:manage → 403."""
    with _client_with_perms(["equipos:read_own"]) as client:
        resp = client.post("/api/v1/equipos/masiva", json=_valid_body())
    assert resp.status_code == 403


# ── Creación exitosa → 201 ────────────────────────────────────────────────────

def test_masiva_creates_asignaciones_returns_201(monkeypatch):
    """POST con permiso y datos válidos → 201 con creadas=2."""
    from app.schemas.equipo import AsignacionMasivaResponse
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "asignacion_masiva",
        AsyncMock(return_value=AsignacionMasivaResponse(creadas=2)),
    )
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.post("/api/v1/equipos/masiva", json=_valid_body())
    assert resp.status_code == 201
    assert resp.json() == {"creadas": 2}


# ── Contexto otro tenant → 422 ────────────────────────────────────────────────

def test_masiva_otro_tenant_returns_422(monkeypatch):
    """Contexto de otro tenant → 422."""
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "asignacion_masiva",
        AsyncMock(side_effect=HTTPException(status_code=422, detail="cohorte_id no pertenece al tenant")),
    )
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.post("/api/v1/equipos/masiva", json=_valid_body())
    assert resp.status_code == 422


# ── Lista vacía → 422 ────────────────────────────────────────────────────────

def test_masiva_empty_usuario_ids_returns_422():
    """usuario_ids: [] → 422 Unprocessable Entity (validación Pydantic)."""
    body = _valid_body()
    body["usuario_ids"] = []
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.post("/api/v1/equipos/masiva", json=body)
    assert resp.status_code == 422


# ── Triangulación: un solo usuario → 201 con creadas=1 ───────────────────────

def test_masiva_single_usuario_returns_201(monkeypatch):
    """POST con un solo usuario_id → 201 con creadas=1."""
    from app.schemas.equipo import AsignacionMasivaResponse
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "asignacion_masiva",
        AsyncMock(return_value=AsignacionMasivaResponse(creadas=1)),
    )
    body = _valid_body()
    body["usuario_ids"] = [str(uuid.uuid4())]
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.post("/api/v1/equipos/masiva", json=body)
    assert resp.status_code == 201
    assert resp.json()["creadas"] == 1
