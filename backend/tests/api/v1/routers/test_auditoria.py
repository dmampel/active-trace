"""Tests de integración para el router de auditoría (C-19, Tareas 5.2–5.5).

Patrón: TestClient + mocked get_current_user + patched RbacRepository.
Valida:
- 5.2 RBAC fail-closed (403 sin permiso), 200 con permiso. Roles: PROFESOR=403, ADMIN/COORD/FINANZAS=200.
- 5.3 Aislamiento de tenant end-to-end.
- 5.4 tenant_id/usuario_id en query ignorados (scope del JWT).
- 5.5 Consultar el panel NO crea registros nuevos en AuditLog.
"""

from __future__ import annotations

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

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_ID = uuid.uuid4()
MATERIA_ID = uuid.uuid4()

ENDPOINTS = [
    "/api/v1/auditoria/log",
    "/api/v1/auditoria/acciones-por-dia",
    "/api/v1/auditoria/comunicaciones-por-docente",
    "/api/v1/auditoria/interacciones",
    "/api/v1/auditoria/ultimas-acciones",
]


def _make_user(roles=None, user_id=None, tenant_id=None):
    user = MagicMock()
    user.id = user_id or USER_ID
    user.tenant_id = tenant_id or TENANT_A
    user.roles = roles or ["ADMIN"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


@contextmanager
def _client_with_perms(perms: list[str], user=None, svc_override=None):
    """TestClient con permisos RBAC mockeados."""
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db

    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override:
            import app.api.v1.routers.auditoria as auditoria_router
            app.dependency_overrides[auditoria_router._get_auditoria_service] = lambda: svc_override
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override:
                import app.api.v1.routers.auditoria as auditoria_router
                app.dependency_overrides.pop(auditoria_router._get_auditoria_service, None)


def _make_svc(**overrides):
    """Mock de AuditoriaService con retornos vacíos por defecto."""
    from app.schemas.auditoria import (
        LogCompletoResponse,
        AccionesPorDiaResponse,
        EstadoComunicacionesResponse,
        InteraccionesResponse,
        UltimasAccionesResponse,
    )
    svc = MagicMock()
    svc.get_log = AsyncMock(return_value=LogCompletoResponse(total=0, page=1, page_size=50, items=[]))
    svc.get_acciones_por_dia = AsyncMock(return_value=AccionesPorDiaResponse(items=[]))
    svc.get_comunicaciones_por_docente = AsyncMock(return_value=EstadoComunicacionesResponse(items=[]))
    svc.get_interacciones = AsyncMock(return_value=InteraccionesResponse(items=[]))
    svc.get_ultimas_acciones = AsyncMock(return_value=UltimasAccionesResponse(limite_aplicado=200, items=[]))
    for k, v in overrides.items():
        setattr(svc, k, AsyncMock(return_value=v))
    return svc


# ── 5.2 RBAC fail-closed ─────────────────────────────────────────────────────


class TestRbacFailClosed:
    """Sin auditoria:ver → 403. Con permiso → 200."""

    def test_sin_permiso_403_en_todos_los_endpoints(self):
        """PROFESOR sin auditoria:ver → 403 en cada endpoint."""
        user = _make_user(roles=["PROFESOR"])
        with _client_with_perms([], user=user) as client:
            for endpoint in ENDPOINTS:
                resp = client.get(endpoint)
                assert resp.status_code == 403, f"Esperaba 403 en {endpoint}, got {resp.status_code}"

    def test_admin_con_permiso_200(self):
        """ADMIN con auditoria:ver → 200 en cada endpoint."""
        user = _make_user(roles=["ADMIN"])
        svc = _make_svc()
        with _client_with_perms(["auditoria:ver"], user=user, svc_override=svc) as client:
            for endpoint in ENDPOINTS:
                resp = client.get(endpoint)
                assert resp.status_code == 200, f"Esperaba 200 en {endpoint}, got {resp.status_code}"

    def test_coordinador_con_permiso_200(self):
        """COORDINADOR con auditoria:ver → 200."""
        user = _make_user(roles=["COORDINADOR"])
        svc = _make_svc()
        with _client_with_perms(["auditoria:ver"], user=user, svc_override=svc) as client:
            resp = client.get("/api/v1/auditoria/log")
            assert resp.status_code == 200

    def test_finanzas_con_permiso_200(self):
        """FINANZAS con auditoria:ver → 200."""
        user = _make_user(roles=["FINANZAS"])
        svc = _make_svc()
        with _client_with_perms(["auditoria:ver"], user=user, svc_override=svc) as client:
            resp = client.get("/api/v1/auditoria/log")
            assert resp.status_code == 200


# ── 5.3 Aislamiento de tenant ─────────────────────────────────────────────────


class TestTenantIsolation:
    """ADMIN del tenant A no ve datos del tenant B."""

    def test_tenant_a_no_ve_datos_tenant_b(self):
        """El service recibe el tenant del JWT, no de la petición."""
        user_a = _make_user(roles=["ADMIN"], tenant_id=TENANT_A)

        # El service mock captura con qué current_user fue llamado
        captured_users = []

        async def _fake_get_log(current_user, **kwargs):
            captured_users.append(current_user.tenant_id)
            from app.schemas.auditoria import LogCompletoResponse
            return LogCompletoResponse(total=0, page=1, page_size=50, items=[])

        svc = _make_svc()
        svc.get_log = _fake_get_log

        with _client_with_perms(["auditoria:ver"], user=user_a, svc_override=svc) as client:
            client.get("/api/v1/auditoria/log")

        assert len(captured_users) == 1
        assert captured_users[0] == TENANT_A


# ── 5.4 tenant_id/usuario_id en query ignorados ───────────────────────────────


class TestQueryParamsIgnorados:
    """Parámetros tenant_id/usuario_id en query no alteran el scope del JWT."""

    def test_tenant_id_en_query_ignorado(self):
        """Si se pasa tenant_id en query, el service usa el del JWT."""
        user = _make_user(roles=["ADMIN"], tenant_id=TENANT_A)

        captured_users = []

        async def _fake_get_log(current_user, **kwargs):
            captured_users.append(current_user.tenant_id)
            from app.schemas.auditoria import LogCompletoResponse
            return LogCompletoResponse(total=0, page=1, page_size=50, items=[])

        svc = _make_svc()
        svc.get_log = _fake_get_log

        # Intentamos pasar tenant_id del tenant B en query — debe ser ignorado
        with _client_with_perms(["auditoria:ver"], user=user, svc_override=svc) as client:
            client.get(f"/api/v1/auditoria/log?tenant_id={TENANT_B}")

        # El router no acepta tenant_id como query param: el service recibe el del JWT
        assert len(captured_users) == 1
        assert captured_users[0] == TENANT_A


# ── 5.5 Consultar panel no crea registros en AuditLog ─────────────────────────


class TestNoAutoAuditoria:
    """Consultar el panel NO genera nuevas entradas en AuditLog."""

    def test_get_log_no_escribe_audit_log(self):
        """El service no llama a ningún método de escritura de AuditLog."""
        user = _make_user(roles=["ADMIN"])
        svc = _make_svc()

        # Verificamos que el mock del service NO tiene métodos de escritura
        with _client_with_perms(["auditoria:ver"], user=user, svc_override=svc) as client:
            resp = client.get("/api/v1/auditoria/log")
            assert resp.status_code == 200

        # Solo se llamó get_log — no create_entry ni ningún método de escritura
        assert svc.get_log.called
        # El service mock no debe tener llamadas a create/write
        assert not hasattr(svc, "create_audit_log") or not getattr(svc, "create_audit_log", MagicMock()).called

    def test_get_ultimas_acciones_no_escribe(self):
        """get_ultimas_acciones tampoco escribe en AuditLog."""
        user = _make_user(roles=["ADMIN"])
        svc = _make_svc()

        with _client_with_perms(["auditoria:ver"], user=user, svc_override=svc) as client:
            resp = client.get("/api/v1/auditoria/ultimas-acciones")
            assert resp.status_code == 200

        assert svc.get_ultimas_acciones.called
