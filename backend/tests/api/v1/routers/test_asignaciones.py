"""Tests de integración para el router de asignaciones.

Tasks 7.5:
  - POST → 201 crear; GET con filtros → 200; PATCH → 200; DELETE → 204
  - Sin permiso → 403
  - Contexto de otro tenant → 422/404
"""
import uuid
import os
from contextlib import contextmanager
from datetime import date
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


def _mock_asig_read():
    from app.schemas.asignacion import AsignacionRead
    return AsignacionRead(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        usuario_id=uuid.uuid4(),
        rol="PROFESOR",
        desde=date.today(),
        hasta=None,
        comisiones=[],
        estado_vigencia="Vigente",
    )


# ── Sin permiso → 403 ─────────────────────────────────────────────────────────

def test_get_asignaciones_no_permission_returns_403():
    """Sin permiso equipos:asignar → 403."""
    with _client_with_perms([]) as client:
        resp = client.get("/api/v1/asignaciones")
    assert resp.status_code == 403


def test_get_asignaciones_no_token_returns_401():
    """Sin token → 401."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/asignaciones")
    assert resp.status_code == 401


# ── POST /asignaciones → 201 ─────────────────────────────────────────────────

def test_post_asignacion_returns_201(monkeypatch):
    """POST con permiso y datos válidos → 201."""
    mock_asig = _mock_asig_read()
    from app.services import asignacion_service as svc_mod
    monkeypatch.setattr(
        svc_mod.AsignacionService, "create",
        AsyncMock(return_value=mock_asig),
    )
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.post(
            "/api/v1/asignaciones",
            json={
                "usuario_id": str(uuid.uuid4()),
                "rol": "PROFESOR",
                "desde": str(date.today()),
            },
        )
    assert resp.status_code == 201


# ── GET /asignaciones con filtros → 200 ──────────────────────────────────────

def test_get_asignaciones_returns_list(monkeypatch):
    """GET lista → 200."""
    mock_asig = _mock_asig_read()
    from app.services import asignacion_service as svc_mod
    monkeypatch.setattr(
        svc_mod.AsignacionService, "list_asignaciones",
        AsyncMock(return_value=[mock_asig]),
    )
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.get("/api/v1/asignaciones")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ── GET /asignaciones/{id} → 200 ────────────────────────────────────────────

def test_get_asignacion_detail_returns_200(monkeypatch):
    """GET detalle por id → 200."""
    mock_asig = _mock_asig_read()
    from app.services import asignacion_service as svc_mod
    monkeypatch.setattr(
        svc_mod.AsignacionService, "get_detail",
        AsyncMock(return_value=mock_asig),
    )
    aid = uuid.uuid4()
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.get(f"/api/v1/asignaciones/{aid}")
    assert resp.status_code == 200


# ── PATCH /asignaciones/{id} → 200 ──────────────────────────────────────────

def test_patch_asignacion_returns_200(monkeypatch):
    """PATCH → 200."""
    mock_asig = _mock_asig_read()
    from app.services import asignacion_service as svc_mod
    monkeypatch.setattr(
        svc_mod.AsignacionService, "update",
        AsyncMock(return_value=mock_asig),
    )
    aid = uuid.uuid4()
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.patch(f"/api/v1/asignaciones/{aid}", json={"rol": "TUTOR"})
    assert resp.status_code == 200


# ── DELETE /asignaciones/{id} → 204 ─────────────────────────────────────────

def test_delete_asignacion_returns_204(monkeypatch):
    """DELETE → 204."""
    from app.services import asignacion_service as svc_mod
    monkeypatch.setattr(
        svc_mod.AsignacionService, "soft_delete",
        AsyncMock(return_value=None),
    )
    aid = uuid.uuid4()
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.delete(f"/api/v1/asignaciones/{aid}")
    assert resp.status_code == 204


# ── Contexto otro tenant → 404 ───────────────────────────────────────────────

def test_get_asignacion_other_tenant_returns_404(monkeypatch):
    """Asignación de otro tenant → 404."""
    from app.services import asignacion_service as svc_mod
    monkeypatch.setattr(
        svc_mod.AsignacionService, "get_detail",
        AsyncMock(side_effect=HTTPException(status_code=404, detail="Asignación no encontrada")),
    )
    aid = uuid.uuid4()
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.get(f"/api/v1/asignaciones/{aid}")
    assert resp.status_code == 404


# ── Schema rechaza campo extra → 422 ─────────────────────────────────────────

def test_post_asignacion_extra_field_returns_422():
    """Campo no declarado en body → 422."""
    with _client_with_perms(["equipos:asignar"]) as client:
        resp = client.post(
            "/api/v1/asignaciones",
            json={
                "usuario_id": str(uuid.uuid4()),
                "rol": "PROFESOR",
                "desde": str(date.today()),
                "campo_extra": "invalido",
            },
        )
    assert resp.status_code == 422
