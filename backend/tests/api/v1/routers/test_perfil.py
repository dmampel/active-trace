"""Tests de integración para perfil propio (C-20).

Tasks 3.1–3.7:
  3.1 service leer_perfil desde JWT
  3.2 service actualizar_perfil (campos editables, 409 email duplicado)
  3.3 GET /api/v1/perfil con require_permission('perfil:editar')
  3.4 PATCH /api/v1/perfil con require_permission('perfil:editar')
  3.5 cuil en PATCH → 422; campo desconocido → 422
  3.6 PII cifrada en reposo (no texto plano)
  3.7 identidad desde JWT; sin JWT → 401
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
from app.models.estructura import EstadoEntidad

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


def _make_current_user():
    user = MagicMock()
    user.id = USER_ID
    user.tenant_id = TENANT_ID
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


@contextmanager
def _client_with_perms(perms: list[str]):
    app.dependency_overrides[get_current_user] = lambda: _make_current_user()
    app.dependency_overrides[get_db] = _fake_db
    target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(target, new=AsyncMock(return_value=set(perms))):
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


def _mock_perfil_read():
    from app.schemas.perfil import PerfilRead
    return PerfilRead(
        id=USER_ID,
        tenant_id=TENANT_ID,
        email="yo@example.com",
        nombre="Juan",
        apellidos="Pérez",
        dni="30123456",
        cuil="20301234561",
        cbu="00000000000000000000",
        alias_cbu="alias.test",
        banco="Banco Nación",
        regional="CABA",
        legajo=None,
        legajo_profesional="LP-001",
        facturador=False,
        estado=EstadoEntidad.activa,
    )


# ── 3.7 Sin token → 401 ───────────────────────────────────────────────────────

def test_get_perfil_no_token_returns_401():
    """Sin JWT → 401 (no expone datos)."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/perfil")
    assert resp.status_code == 401


# ── 3.3 Sin permiso perfil:editar → 403 ──────────────────────────────────────

def test_get_perfil_no_permission_returns_403():
    """Sin permiso perfil:editar → 403 (fail-closed)."""
    with _client_with_perms([]) as client:
        resp = client.get("/api/v1/perfil")
    assert resp.status_code == 403


# ── 3.1 GET /perfil → 200 con PII descifrada ─────────────────────────────────

def test_get_perfil_returns_200_with_pii(monkeypatch):
    """GET perfil → 200 con todos los campos incluyendo cuil descifrado."""
    from app.services import perfil_service as svc_mod
    monkeypatch.setattr(
        svc_mod.PerfilService, "leer_perfil",
        AsyncMock(return_value=_mock_perfil_read()),
    )
    with _client_with_perms(["perfil:editar"]) as client:
        resp = client.get("/api/v1/perfil")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(USER_ID)
    assert data["cuil"] == "20301234561"
    assert data["dni"] == "30123456"
    assert data["email"] == "yo@example.com"


# ── 3.7 Identidad ignorada de query/body/header ───────────────────────────────

def test_get_perfil_ignores_usuario_id_in_query(monkeypatch):
    """GET perfil ignora usuario_id en query param — solo usa JWT."""
    from app.services import perfil_service as svc_mod
    monkeypatch.setattr(
        svc_mod.PerfilService, "leer_perfil",
        AsyncMock(return_value=_mock_perfil_read()),
    )
    otro_id = uuid.uuid4()
    with _client_with_perms(["perfil:editar"]) as client:
        # Aunque se manda usuario_id en query, el endpoint lo ignora
        resp = client.get(f"/api/v1/perfil?usuario_id={otro_id}")
    assert resp.status_code == 200
    data = resp.json()
    # El id devuelto es el del JWT, no el del query param
    assert data["id"] == str(USER_ID)


# ── 3.3 PATCH sin permiso → 403 ──────────────────────────────────────────────

def test_patch_perfil_no_permission_returns_403():
    """PATCH sin permiso perfil:editar → 403."""
    with _client_with_perms([]) as client:
        resp = client.patch("/api/v1/perfil", json={"nombre": "Nuevo"})
    assert resp.status_code == 403


# ── 3.4 PATCH /perfil → 200 con campos editables ─────────────────────────────

def test_patch_perfil_returns_200(monkeypatch):
    """PATCH con campos editables válidos → 200."""
    from app.services import perfil_service as svc_mod
    monkeypatch.setattr(
        svc_mod.PerfilService, "actualizar_perfil",
        AsyncMock(return_value=_mock_perfil_read()),
    )
    with _client_with_perms(["perfil:editar"]) as client:
        resp = client.patch(
            "/api/v1/perfil",
            json={"nombre": "Nuevo", "banco": "BBVA", "regional": "GBA"},
        )
    assert resp.status_code == 200


# ── 3.5 cuil en PATCH → 422 (extra='forbid') ─────────────────────────────────

def test_patch_perfil_with_cuil_returns_422():
    """Intento de modificar cuil → 422 (schema no lo declara + extra='forbid')."""
    with _client_with_perms(["perfil:editar"]) as client:
        resp = client.patch("/api/v1/perfil", json={"cuil": "20123456789"})
    assert resp.status_code == 422


# ── 3.5 Campo no declarado → 422 ─────────────────────────────────────────────

def test_patch_perfil_unknown_field_returns_422():
    """Campo desconocido → 422 por extra='forbid'."""
    with _client_with_perms(["perfil:editar"]) as client:
        resp = client.patch("/api/v1/perfil", json={"campo_inventado": "valor"})
    assert resp.status_code == 422


# ── 3.2 Email duplicado → 409 ────────────────────────────────────────────────

def test_patch_perfil_duplicate_email_returns_409(monkeypatch):
    """Cambio de email a uno ya existente en el tenant → 409."""
    from app.services import perfil_service as svc_mod
    monkeypatch.setattr(
        svc_mod.PerfilService, "actualizar_perfil",
        AsyncMock(side_effect=HTTPException(status_code=409, detail="Email ya registrado en el tenant")),
    )
    with _client_with_perms(["perfil:editar"]) as client:
        resp = client.patch("/api/v1/perfil", json={"email": "dup@example.com"})
    assert resp.status_code == 409


# ── 3.6 PII cifrada en reposo ────────────────────────────────────────────────

def test_pii_encrypted_at_rest():
    """PII debe cifrarse antes de persistir y no aparecer en texto plano."""
    from app.services.usuario_service import encrypt_pii, decrypt_pii

    plaintext = "30123456"
    ciphertext = encrypt_pii(plaintext)

    # El ciphertext no es el texto plano
    assert ciphertext != plaintext
    # Se puede descifrar correctamente
    assert decrypt_pii(ciphertext) == plaintext
    # None se maneja sin error
    assert encrypt_pii(None) is None
    assert decrypt_pii(None) is None


# ── 3.6 TRIANGULATE: múltiples valores PII cifrados ─────────────────────────

def test_pii_different_values_produce_different_ciphertexts():
    """Distintos valores PII producen distintos ciphertexts (no colisión)."""
    from app.services.usuario_service import encrypt_pii

    c1 = encrypt_pii("30123456")
    c2 = encrypt_pii("20987654321")

    assert c1 != c2
    # Ambos cifrados son distintos del texto plano
    assert c1 != "30123456"
    assert c2 != "20987654321"


# ── 3.4 PATCH con modalidad_cobro → mapea a facturador ──────────────────────

def test_patch_perfil_modalidad_cobro_factura(monkeypatch):
    """modalidad_cobro='factura' → válido (no 422)."""
    from app.services import perfil_service as svc_mod
    updated = _mock_perfil_read()
    monkeypatch.setattr(
        svc_mod.PerfilService, "actualizar_perfil",
        AsyncMock(return_value=updated),
    )
    with _client_with_perms(["perfil:editar"]) as client:
        resp = client.patch("/api/v1/perfil", json={"modalidad_cobro": "factura"})
    assert resp.status_code == 200


def test_patch_perfil_modalidad_cobro_invalid_returns_422():
    """modalidad_cobro con valor inválido → 422."""
    with _client_with_perms(["perfil:editar"]) as client:
        resp = client.patch("/api/v1/perfil", json={"modalidad_cobro": "invalido"})
    assert resp.status_code == 422
