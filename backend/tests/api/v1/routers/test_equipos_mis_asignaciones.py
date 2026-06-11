"""Tests de integración para GET /api/v1/equipos/mis-asignaciones.

TDD cycle:
  RED: escribir tests que describen comportamiento esperado
  GREEN: validar que el código implementado los satisface
  TRIANGULATE: múltiples casos para forzar lógica real

Safety net: 119 tests pasando antes de C-08.
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


def _mock_asignacion_detalle():
    from app.schemas.equipo import AsignacionDetalleResponse
    return AsignacionDetalleResponse(
        id=uuid.uuid4(),
        rol="PROFESOR",
        materia="Matemáticas I",
        carrera="Ingeniería en Sistemas",
        cohorte="2024",
        desde=date.today(),
        hasta=None,
        estado_vigencia="Vigente",
        responsable_id=None,
    )


# ── Sin permiso → 403 ─────────────────────────────────────────────────────────

def test_mis_asignaciones_no_permission_returns_403():
    """Sin permiso equipos:read_own → 403."""
    with _client_with_perms([]) as client:
        resp = client.get("/api/v1/equipos/mis-asignaciones")
    assert resp.status_code == 403


def test_mis_asignaciones_no_token_returns_401():
    """Sin token → 401."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/equipos/mis-asignaciones")
    assert resp.status_code == 401


# ── Lista propia → 200 ────────────────────────────────────────────────────────

def test_mis_asignaciones_returns_list(monkeypatch):
    """GET con permiso → 200 lista de asignaciones propias."""
    mock_result = [_mock_asignacion_detalle()]
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "mis_asignaciones",
        AsyncMock(return_value=mock_result),
    )
    with _client_with_perms(["equipos:read_own"]) as client:
        resp = client.get("/api/v1/equipos/mis-asignaciones")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["rol"] == "PROFESOR"
    assert data[0]["estado_vigencia"] == "Vigente"


# ── Filtro por rol ────────────────────────────────────────────────────────────

def test_mis_asignaciones_filtro_rol(monkeypatch):
    """GET ?rol=TUTOR → service recibe el filtro."""
    from app.services import equipo_service as svc_mod
    mock_svc = AsyncMock(return_value=[])
    monkeypatch.setattr(svc_mod.EquipoService, "mis_asignaciones", mock_svc)
    with _client_with_perms(["equipos:read_own"]) as client:
        resp = client.get("/api/v1/equipos/mis-asignaciones?rol=TUTOR")
    assert resp.status_code == 200
    # Verificar que el filtro llegó al service
    mock_svc.assert_called_once()
    _, kwargs = mock_svc.call_args
    assert kwargs.get("rol") == "TUTOR"


# ── Lista vacía → 200 [] ──────────────────────────────────────────────────────

def test_mis_asignaciones_empty_returns_200(monkeypatch):
    """Sin asignaciones → 200 lista vacía."""
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "mis_asignaciones",
        AsyncMock(return_value=[]),
    )
    with _client_with_perms(["equipos:read_own"]) as client:
        resp = client.get("/api/v1/equipos/mis-asignaciones")
    assert resp.status_code == 200
    assert resp.json() == []


# ── Filtro por materia_id ─────────────────────────────────────────────────────

def test_mis_asignaciones_filtro_materia(monkeypatch):
    """GET ?materia_id=<uuid> → service recibe el filtro."""
    materia_id = uuid.uuid4()
    from app.services import equipo_service as svc_mod
    mock_svc = AsyncMock(return_value=[])
    monkeypatch.setattr(svc_mod.EquipoService, "mis_asignaciones", mock_svc)
    with _client_with_perms(["equipos:read_own"]) as client:
        resp = client.get(f"/api/v1/equipos/mis-asignaciones?materia_id={materia_id}")
    assert resp.status_code == 200
    mock_svc.assert_called_once()
    _, kwargs = mock_svc.call_args
    assert kwargs.get("materia_id") == materia_id
