"""Tests de integración para GET /api/v1/equipos/exportar.

TDD scenarios:
  - Export CSV exitoso → content-type text/csv + headers correctos
  - Sin permiso equipos:export → 403
  - Con permiso equipos:manage (incorrecto) → 403
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

from fastapi.responses import StreamingResponse
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


def _csv_response():
    """Genera un StreamingResponse CSV mínimo para tests."""
    csv_content = (
        "nombre,apellido,legajo,rol,materia,carrera,cohorte,desde,hasta,estado_vigencia\r\n"
        "Juan,García,12345,PROFESOR,Matemáticas,Ingeniería,2024,2024-03-01,,Vigente\r\n"
    )

    def _gen():
        yield csv_content

    return StreamingResponse(
        _gen(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="equipo.csv"'},
    )


# ── Sin permiso → 403 ─────────────────────────────────────────────────────────

def test_exportar_no_permission_returns_403():
    """Sin permiso equipos:export → 403."""
    with _client_with_perms(["equipos:manage"]) as client:
        resp = client.get("/api/v1/equipos/exportar")
    assert resp.status_code == 403


def test_exportar_no_token_returns_401():
    """Sin token → 401."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/equipos/exportar")
    assert resp.status_code == 401


# ── Export exitoso → content-type text/csv ────────────────────────────────────

def test_exportar_returns_csv_content_type(monkeypatch):
    """GET con permiso equipos:export → content-type text/csv."""
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "exportar_csv",
        AsyncMock(return_value=_csv_response()),
    )
    with _client_with_perms(["equipos:export"]) as client:
        resp = client.get("/api/v1/equipos/exportar")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


# ── Content-Disposition attachment ───────────────────────────────────────────

def test_exportar_returns_attachment_header(monkeypatch):
    """GET con permiso → Content-Disposition: attachment; filename='equipo.csv'."""
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "exportar_csv",
        AsyncMock(return_value=_csv_response()),
    )
    with _client_with_perms(["equipos:export"]) as client:
        resp = client.get("/api/v1/equipos/exportar")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "equipo.csv" in resp.headers.get("content-disposition", "")


# ── Headers CSV correctos ─────────────────────────────────────────────────────

def test_exportar_csv_has_correct_headers(monkeypatch):
    """El CSV retornado contiene los headers esperados en la primera línea."""
    from app.services import equipo_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EquipoService, "exportar_csv",
        AsyncMock(return_value=_csv_response()),
    )
    with _client_with_perms(["equipos:export"]) as client:
        resp = client.get("/api/v1/equipos/exportar")
    assert resp.status_code == 200
    first_line = resp.text.split("\n")[0]
    for col in ["nombre", "apellido", "legajo", "rol", "materia", "carrera", "cohorte"]:
        assert col in first_line
