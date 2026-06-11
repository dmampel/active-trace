"""Tests de integración para los filtros nuevos en GET /api/v1/asignaciones.

TDD scenarios (C-08 extiende el endpoint existente con carrera_id):
  - carrera_id como filtro → service lo recibe
  - carrera_id + cohorte_id juntos → ambos pasan al service
  - materia_id como filtro → service lo recibe
  - rol como filtro → service lo recibe
"""
import uuid
import os
from contextlib import contextmanager
from datetime import date
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


# ── Filtro carrera_id → 200, filtro recibido ─────────────────────────────────

def test_get_asignaciones_filtro_carrera_id(monkeypatch):
    """GET /asignaciones?carrera_id=<uuid> → service recibe carrera_id."""
    from app.services import asignacion_service as svc_mod
    mock_svc = AsyncMock(return_value=[])
    monkeypatch.setattr(svc_mod.AsignacionService, "list_asignaciones", mock_svc)
    carrera_id = uuid.uuid4()
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.get(f"/api/v1/asignaciones?carrera_id={carrera_id}")
    assert resp.status_code == 200
    mock_svc.assert_called_once()
    _, kwargs = mock_svc.call_args
    assert kwargs.get("carrera_id") == carrera_id


# ── Filtro carrera_id + cohorte_id ───────────────────────────────────────────

def test_get_asignaciones_filtro_carrera_y_cohorte(monkeypatch):
    """GET /asignaciones?carrera_id=<uuid>&cohorte_id=<uuid> → ambos pasan."""
    from app.services import asignacion_service as svc_mod
    mock_svc = AsyncMock(return_value=[])
    monkeypatch.setattr(svc_mod.AsignacionService, "list_asignaciones", mock_svc)
    carrera_id = uuid.uuid4()
    cohorte_id = uuid.uuid4()
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.get(
            f"/api/v1/asignaciones?carrera_id={carrera_id}&cohorte_id={cohorte_id}"
        )
    assert resp.status_code == 200
    _, kwargs = mock_svc.call_args
    assert kwargs.get("carrera_id") == carrera_id
    assert kwargs.get("cohorte_id") == cohorte_id


# ── Filtro materia_id ─────────────────────────────────────────────────────────

def test_get_asignaciones_filtro_materia_id(monkeypatch):
    """GET /asignaciones?materia_id=<uuid> → service recibe materia_id."""
    from app.services import asignacion_service as svc_mod
    mock_svc = AsyncMock(return_value=[])
    monkeypatch.setattr(svc_mod.AsignacionService, "list_asignaciones", mock_svc)
    materia_id = uuid.uuid4()
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.get(f"/api/v1/asignaciones?materia_id={materia_id}")
    assert resp.status_code == 200
    _, kwargs = mock_svc.call_args
    assert kwargs.get("materia_id") == materia_id


# ── Filtro rol ────────────────────────────────────────────────────────────────

def test_get_asignaciones_filtro_rol(monkeypatch):
    """GET /asignaciones?rol=PROFESOR → service recibe rol='PROFESOR'."""
    from app.services import asignacion_service as svc_mod
    mock_svc = AsyncMock(return_value=[])
    monkeypatch.setattr(svc_mod.AsignacionService, "list_asignaciones", mock_svc)
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.get("/api/v1/asignaciones?rol=PROFESOR")
    assert resp.status_code == 200
    _, kwargs = mock_svc.call_args
    assert kwargs.get("rol") == "PROFESOR"
