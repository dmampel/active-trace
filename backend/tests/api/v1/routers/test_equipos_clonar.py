"""Tests de integración para POST /api/v1/equipos/clonar.

TDD scenarios:
  - Clonado exitoso → 201 con { "clonadas": N, "omitidas": M }
  - Duplicados omitidos (omitidas > 0) → 201
  - Origen = destino → 422
  - Sin asignaciones vigentes → 201 con clonadas=0, omitidas=0
  - Sin permiso → 403
"""
import uuid
import os
from contextlib import contextmanager
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
        "origen": {"cohorte_id": str(uuid.uuid4())},
        "destino": {"cohorte_id": str(uuid.uuid4())},
    }


# ── Sin permiso → 403 ─────────────────────────────────────────────────────────

def test_clonar_no_permission_returns_403():
    """Sin permiso equipos:manage → 403."""
    with _client_with_perms(["equipos:read_own"]) as client:
        resp = client.post("/api/v1/equipos/clonar", json=_valid_body())
    assert resp.status_code == 403


# ── Clonado exitoso → 201 ────────────────────────────────────────────────────

def test_clonar_exitoso_returns_201(monkeypatch):
    """POST con origen y destino válidos → 201 con clonadas=3, omitidas=0."""
    from app.schemas.equipo import ClonarEquipoResponse
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "clonar_equipo",
        AsyncMock(return_value=ClonarEquipoResponse(clonadas=3, omitidas=0)),
    )
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.post("/api/v1/equipos/clonar", json=_valid_body())
    assert resp.status_code == 201
    data = resp.json()
    assert data["clonadas"] == 3
    assert data["omitidas"] == 0


# ── Duplicados omitidos ───────────────────────────────────────────────────────

def test_clonar_duplicados_omitidos_returns_201(monkeypatch):
    """Algunos duplicados existen en destino → clonadas=2, omitidas=1."""
    from app.schemas.equipo import ClonarEquipoResponse
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "clonar_equipo",
        AsyncMock(return_value=ClonarEquipoResponse(clonadas=2, omitidas=1)),
    )
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.post("/api/v1/equipos/clonar", json=_valid_body())
    assert resp.status_code == 201
    data = resp.json()
    assert data["clonadas"] == 2
    assert data["omitidas"] == 1


# ── Origen = destino → 422 ────────────────────────────────────────────────────

def test_clonar_origen_igual_destino_returns_422(monkeypatch):
    """Origen idéntico al destino → 422."""
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "clonar_equipo",
        AsyncMock(
            side_effect=HTTPException(
                status_code=422, detail="El equipo origen y destino no pueden ser idénticos"
            )
        ),
    )
    same_cohorte = str(uuid.uuid4())
    body = {"origen": {"cohorte_id": same_cohorte}, "destino": {"cohorte_id": same_cohorte}}
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.post("/api/v1/equipos/clonar", json=body)
    assert resp.status_code == 422


# ── Sin vigentes en origen → 201 clonadas=0 ──────────────────────────────────

def test_clonar_sin_vigentes_returns_201_zero(monkeypatch):
    """Sin asignaciones vigentes en origen → 201 clonadas=0, omitidas=0."""
    from app.schemas.equipo import ClonarEquipoResponse
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "clonar_equipo",
        AsyncMock(return_value=ClonarEquipoResponse(clonadas=0, omitidas=0)),
    )
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.post("/api/v1/equipos/clonar", json=_valid_body())
    assert resp.status_code == 201
    data = resp.json()
    assert data["clonadas"] == 0
    assert data["omitidas"] == 0
