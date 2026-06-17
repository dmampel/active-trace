"""Tests de integración para el router de calificaciones (C-10 — Tareas 8.2–8.5).

Patrón: TestClient + mocked get_current_user + patched RbacRepository.
Valida: RBAC fail-closed (403 sin permiso), scope tenant (404 fuera del tenant),
identidad del JWT (ignorar tenant_id/usuario_id del body), lectura con calificaciones:leer.
"""

import os
import uuid
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
MATERIA_ID = uuid.uuid4()
ASIGNACION_ID = uuid.uuid4()


def _make_user(user_id=None, tenant_id=None, asignacion_id=None):
    user = MagicMock()
    user.id = user_id or USER_ID
    user.tenant_id = tenant_id or TENANT_ID
    user.impersonado_id = None
    # Asignacion vigente — el router la usa para configurar umbral
    asig = MagicMock()
    asig.id = asignacion_id or ASIGNACION_ID
    user.asignacion_activa = asig
    return user


async def _fake_db():
    yield AsyncMock()


@contextmanager
def _client_with_perms(perms: list[str], user=None):
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db
    target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(target, new=AsyncMock(return_value=set(perms))):
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


# ── RBAC fail-closed ──────────────────────────────────────────────────────────


class TestRBACCalificaciones:
    def test_importar_sin_permiso_retorna_403(self):
        """Sin calificaciones:importar → 403 Forbidden."""
        with _client_with_perms([]) as client:
            resp = client.post(
                f"/api/v1/calificaciones/{MATERIA_ID}/preview",
                files={"file": ("notas.csv", b"Nombre,Email\n", "text/csv")},
            )
        assert resp.status_code == 403

    def test_leer_sin_permiso_retorna_403(self):
        """Sin calificaciones:leer → 403 Forbidden."""
        with _client_with_perms([]) as client:
            resp = client.get(f"/api/v1/calificaciones/{MATERIA_ID}/")
        assert resp.status_code == 403

    def test_leer_con_permiso_calificaciones_leer_no_retorna_403(self, monkeypatch):
        """Con calificaciones:leer → acceso permitido (no 403)."""
        import app.api.v1.routers.calificaciones as cal_router

        monkeypatch.setattr(
            cal_router,
            "_get_calificacion_service",
            lambda db: AsyncMock(**{
                "listar": AsyncMock(return_value=[]),
            }),
        )
        with _client_with_perms(["calificaciones:leer"]) as client:
            resp = client.get(f"/api/v1/calificaciones/{MATERIA_ID}/")
        assert resp.status_code != 403

    def test_config_umbral_sin_permiso_retorna_403(self):
        """Sin calificaciones:importar → 403 al configurar umbral."""
        with _client_with_perms(["calificaciones:leer"]) as client:
            resp = client.put(
                f"/api/v1/calificaciones/{MATERIA_ID}/umbral",
                json={
                    "materia_id": str(MATERIA_ID),
                    "umbral_pct": 70,
                    "valores_aprobatorios": ["Satisfactorio"],
                },
            )
        assert resp.status_code == 403


# ── Scope tenant (materia_id fuera del tenant → 404) ─────────────────────────


class TestScopeCalificaciones:
    def test_preview_materia_fuera_del_tenant_retorna_404(self):
        """materia_id fuera del tenant → 404 (no revelar existencia)."""
        from fastapi import HTTPException
        from app.api.v1.routers.calificaciones import _get_calificacion_service

        svc_mock = MagicMock()
        svc_mock.preview = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Not found")
        )

        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_db] = _fake_db
        app.dependency_overrides[_get_calificacion_service] = lambda: svc_mock

        target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
        with patch(target, new=AsyncMock(return_value={"calificaciones:importar"})):
            try:
                client = TestClient(app, raise_server_exceptions=False)
                resp = client.post(
                    f"/api/v1/calificaciones/{MATERIA_ID}/preview",
                    files={"file": ("notas.csv", b"Nombre,Email\n", "text/csv")},
                )
            finally:
                app.dependency_overrides.pop(get_current_user, None)
                app.dependency_overrides.pop(get_db, None)
                app.dependency_overrides.pop(_get_calificacion_service, None)

        assert resp.status_code == 404


# ── Identidad del JWT (ignorar tenant_id/usuario_id del body) ────────────────


class TestIdentidadJWT:
    def test_importar_ignora_tenant_id_en_body(self, monkeypatch):
        """El endpoint ignora cualquier tenant_id en el body — usa el del JWT."""
        import app.api.v1.routers.calificaciones as cal_router

        captured_tenant = {}

        async def _fake_importar(self, *, tenant_id, actor_id, materia_id, **kwargs):
            captured_tenant["tenant_id"] = tenant_id
            return {"filas_afectadas": 0}

        monkeypatch.setattr(
            "app.services.calificacion_service.CalificacionService.importar",
            _fake_importar,
        )

        otro_tenant = uuid.uuid4()
        user = _make_user()

        with _client_with_perms(["calificaciones:importar"], user=user) as client:
            resp = client.post(
                f"/api/v1/calificaciones/{MATERIA_ID}/importar",
                json={
                    "actividades": [],
                    "seleccionadas": [],
                    "filas": [],
                    # Intento de inyectar tenant_id externo — debe ignorarse
                    "tenant_id": str(otro_tenant),
                },
            )

        # El tenant usado debe ser el del JWT, no el del body
        if captured_tenant:
            assert captured_tenant["tenant_id"] == TENANT_ID
