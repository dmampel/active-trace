"""Tests de integración para PATCH /api/v1/equipos/vigencia.

TDD scenarios:
  - Actualización exitosa → 200 con { "actualizadas": N }
  - Sin asignaciones → 200 con actualizadas=0
  - Sin desde ni hasta → 422
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
        "cohorte_id": str(uuid.uuid4()),
        "hasta": str(date(2025, 12, 31)),
    }


# ── Sin permiso → 403 ─────────────────────────────────────────────────────────

def test_vigencia_no_permission_returns_403():
    """Sin permiso equipos:manage → 403."""
    with _client_with_perms(["equipos:read_own"]) as client:
        resp = client.patch("/api/v1/equipos/vigencia", json=_valid_body())
    assert resp.status_code == 403


# ── Actualización exitosa → 200 ───────────────────────────────────────────────

def test_vigencia_update_returns_200(monkeypatch):
    """PATCH con permiso y datos válidos → 200 con actualizadas=5."""
    from app.schemas.equipo import VigenciaEquipoResponse
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "actualizar_vigencia",
        AsyncMock(return_value=VigenciaEquipoResponse(actualizadas=5)),
    )
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.patch("/api/v1/equipos/vigencia", json=_valid_body())
    assert resp.status_code == 200
    assert resp.json() == {"actualizadas": 5}


# ── Sin asignaciones → 200 actualizadas=0 ────────────────────────────────────

def test_vigencia_sin_asignaciones_returns_200_zero(monkeypatch):
    """Sin asignaciones para el equipo → 200 con actualizadas=0."""
    from app.schemas.equipo import VigenciaEquipoResponse
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "actualizar_vigencia",
        AsyncMock(return_value=VigenciaEquipoResponse(actualizadas=0)),
    )
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.patch("/api/v1/equipos/vigencia", json=_valid_body())
    assert resp.status_code == 200
    assert resp.json()["actualizadas"] == 0


# ── Sin desde ni hasta → 422 (validación Pydantic) ───────────────────────────

def test_vigencia_sin_fechas_returns_422():
    """Body sin desde ni hasta → 422 (model_validator lo captura)."""
    body = {"cohorte_id": str(uuid.uuid4())}
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.patch("/api/v1/equipos/vigencia", json=body)
    assert resp.status_code == 422


# ── Triangulación: solo desde → 200 ──────────────────────────────────────────

def test_vigencia_solo_desde_returns_200(monkeypatch):
    """Body solo con desde (sin hasta) → 200 válido."""
    from app.schemas.equipo import VigenciaEquipoResponse
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "actualizar_vigencia",
        AsyncMock(return_value=VigenciaEquipoResponse(actualizadas=3)),
    )
    body = {"cohorte_id": str(uuid.uuid4()), "desde": str(date.today())}
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.patch("/api/v1/equipos/vigencia", json=body)
    assert resp.status_code == 200
    assert resp.json()["actualizadas"] == 3
