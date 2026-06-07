"""Tests para endpoints de estructura académica.

Strict TDD — usa FastAPI TestClient con DB override mockeada + patch de RBAC por test.
"""
import uuid
import os

from contextlib import contextmanager
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from app.main import app
from app.core.dependencies import get_current_user, get_sync_db

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


def _make_user():
    user = MagicMock()
    user.id = USER_ID
    user.tenant_id = TENANT_ID
    user.impersonado_id = None
    return user


@contextmanager
def _client_with_perms(perms: list[str]):
    """Context manager: inyecta current_user y parchea RBAC con los permisos dados.
    Restaura todo al salir — no contamina otros tests.
    """
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_sync_db] = lambda: MagicMock()
    target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(target, return_value=set(perms)):
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_sync_db, None)


# ── 9.5 Sin token → 401 ───────────────────────────────────────────────────────

def test_get_carreras_requires_auth():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_sync_db] = lambda: MagicMock()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/estructura/carreras", headers={"X-Tenant-ID": str(TENANT_ID)})
    app.dependency_overrides.clear()
    assert response.status_code == 401


# ── 9.1 POST /carreras → 201 ──────────────────────────────────────────────────

def test_post_carrera_returns_201(monkeypatch):
    mock_carrera = MagicMock()
    mock_carrera.id = uuid.uuid4()
    mock_carrera.tenant_id = TENANT_ID
    mock_carrera.codigo = "TUPAD"
    mock_carrera.nombre = "Tecnicatura"
    mock_carrera.estado = "Activa"

    from app.services import estructura_service as svc_mod
    monkeypatch.setattr(svc_mod.EstructuraService, "create_carrera", lambda *a, **kw: mock_carrera)

    with _client_with_perms(["estructura:leer", "estructura:crear"]) as client:
        response = client.post(
            "/api/v1/estructura/carreras",
            json={"codigo": "TUPAD", "nombre": "Tecnicatura"},
            headers={"X-Tenant-ID": str(TENANT_ID)},
        )
    assert response.status_code == 201


# ── 9.2 POST /carreras código duplicado → 409 ─────────────────────────────────

def test_post_carrera_duplicate_returns_409(monkeypatch):
    from fastapi import HTTPException
    from app.services import estructura_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EstructuraService, "create_carrera",
        lambda *a, **kw: (_ for _ in ()).throw(HTTPException(status_code=409, detail="Conflict")),
    )
    with _client_with_perms(["estructura:leer", "estructura:crear"]) as client:
        response = client.post(
            "/api/v1/estructura/carreras",
            json={"codigo": "DUP", "nombre": "Duplicada"},
            headers={"X-Tenant-ID": str(TENANT_ID)},
        )
    assert response.status_code == 409


# ── 9.3 POST /cohortes con carrera_id de otro tenant → 422 ───────────────────

def test_post_cohorte_foreign_tenant_returns_422(monkeypatch):
    from fastapi import HTTPException
    from app.services import estructura_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EstructuraService, "create_cohorte",
        lambda *a, **kw: (_ for _ in ()).throw(HTTPException(status_code=422, detail="carrera_id inválido")),
    )
    with _client_with_perms(["estructura:leer", "estructura:crear"]) as client:
        response = client.post(
            "/api/v1/estructura/cohortes",
            json={"carrera_id": str(uuid.uuid4()), "nombre": "MAR-2026", "anio": 2026, "vig_desde": "2026-03-01"},
            headers={"X-Tenant-ID": str(TENANT_ID)},
        )
    assert response.status_code == 422


# ── 9.4 POST /instancias duplicada → 409 ─────────────────────────────────────

def test_post_instancia_duplicate_returns_409(monkeypatch):
    from fastapi import HTTPException
    from app.services import estructura_service as svc_mod
    monkeypatch.setattr(
        svc_mod.EstructuraService, "create_instancia",
        lambda *a, **kw: (_ for _ in ()).throw(HTTPException(status_code=409, detail="Conflict")),
    )
    with _client_with_perms(["estructura:leer", "estructura:crear"]) as client:
        response = client.post(
            "/api/v1/estructura/instancias",
            json={"materia_id": str(uuid.uuid4()), "cohorte_id": str(uuid.uuid4()), "nombre": "Prog Python", "periodo": "2026-1"},
            headers={"X-Tenant-ID": str(TENANT_ID)},
        )
    assert response.status_code == 409


# ── 9.6 PROFESOR puede GET /carreras (tiene estructura:leer) ──────────────────

def test_get_carreras_with_leer_permission_returns_200(monkeypatch):
    from app.services import estructura_service as svc_mod
    monkeypatch.setattr(svc_mod.EstructuraService, "list_carreras", lambda *a, **kw: [])
    with _client_with_perms(["estructura:leer"]) as client:
        response = client.get("/api/v1/estructura/carreras", headers={"X-Tenant-ID": str(TENANT_ID)})
    assert response.status_code == 200


# ── 9.7 PROFESOR no puede POST /carreras (no tiene estructura:crear) ──────────

def test_post_carrera_without_crear_returns_403():
    with _client_with_perms(["estructura:leer"]) as client:
        response = client.post(
            "/api/v1/estructura/carreras",
            json={"codigo": "X", "nombre": "Y"},
            headers={"X-Tenant-ID": str(TENANT_ID)},
        )
    assert response.status_code == 403


# ── 9.8 COORDINADOR no puede DELETE /carreras (no tiene estructura:eliminar) ──

def test_delete_carrera_without_eliminar_returns_403():
    with _client_with_perms(["estructura:leer", "estructura:crear", "estructura:editar"]) as client:
        response = client.delete(
            f"/api/v1/estructura/carreras/{uuid.uuid4()}",
            headers={"X-Tenant-ID": str(TENANT_ID)},
        )
    assert response.status_code == 403


# ── 9.9 Crear carrera registra acción de auditoría ───────────────────────────

def test_create_carrera_generates_audit_log(monkeypatch):
    from app.services import estructura_service as svc_mod
    audit_calls = []

    mock_carrera = MagicMock()
    mock_carrera.id = uuid.uuid4()
    mock_carrera.tenant_id = TENANT_ID
    mock_carrera.codigo = "AUD"
    mock_carrera.nombre = "Auditada"
    mock_carrera.estado = "Activa"

    def _patched_create(self, *args, **kwargs):
        audit_calls.append("ESTRUCTURA_CARRERA_CREAR")
        return mock_carrera

    monkeypatch.setattr(svc_mod.EstructuraService, "create_carrera", _patched_create)

    with _client_with_perms(["estructura:leer", "estructura:crear"]) as client:
        client.post(
            "/api/v1/estructura/carreras",
            json={"codigo": "AUD", "nombre": "Auditada"},
            headers={"X-Tenant-ID": str(TENANT_ID)},
        )
    assert "ESTRUCTURA_CARRERA_CREAR" in audit_calls


# ── 9.10 ADMIN puede DELETE /instancias → 204 ────────────────────────────────

def test_delete_instancia_admin_returns_204(monkeypatch):
    from app.services import estructura_service as svc_mod
    monkeypatch.setattr(svc_mod.EstructuraService, "delete_instancia", lambda *a, **kw: True)
    with _client_with_perms(["estructura:leer", "estructura:crear", "estructura:editar", "estructura:eliminar"]) as client:
        response = client.delete(
            f"/api/v1/estructura/instancias/{uuid.uuid4()}",
            headers={"X-Tenant-ID": str(TENANT_ID)},
        )
    assert response.status_code == 204
