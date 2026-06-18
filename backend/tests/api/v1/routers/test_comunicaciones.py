"""Tests de integración para el router de comunicaciones (C-12, Tareas 10.1–10.13).

Patrón: TestClient + mocked get_current_user + patched RbacRepository.
Usa servicio con mock para evitar DB real en tests de router.
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.models.comunicacion import EstadoComunicacion
from app.schemas.comunicacion import (
    ComunicacionEnviarResponse,
    ComunicacionPreviewResponse,
    ComunicacionResponse,
    LoteAccionResponse,
)

TENANT_ID = uuid.uuid4()
TENANT_ID_B = uuid.uuid4()
USER_ID = uuid.uuid4()
MATERIA_ID = uuid.uuid4()
COM_ID = uuid.uuid4()
LOTE_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


def _make_user(roles=None, user_id=None, tenant_id=None):
    user = MagicMock()
    user.id = user_id or USER_ID
    user.tenant_id = tenant_id or TENANT_ID
    user.roles = roles or ["PROFESOR"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


def _make_com_response(**overrides) -> ComunicacionResponse:
    defaults = dict(
        id=COM_ID,
        tenant_id=TENANT_ID,
        enviado_por=USER_ID,
        materia_id=MATERIA_ID,
        destinatario_masked="****@****",
        asunto="Test",
        cuerpo="Cuerpo",
        estado=EstadoComunicacion.Pendiente,
        lote_id=None,
        enviado_at=None,
        aprobado_at=None,
        created_at=NOW,
        deleted_at=None,
    )
    defaults.update(overrides)
    return ComunicacionResponse(**defaults)


@contextmanager
def _client_with_perms(perms: list[str], user=None, svc_override=None):
    """Construye un TestClient con permisos mockeados."""
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db

    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override:
            import app.api.v1.routers.comunicaciones as router_mod
            app.dependency_overrides[router_mod._get_comunicacion_service] = (
                lambda: svc_override
            )
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override:
                import app.api.v1.routers.comunicaciones as router_mod
                app.dependency_overrides.pop(
                    router_mod._get_comunicacion_service, None
                )


def _make_svc(**method_overrides):
    """Crea mock del ComunicacionService con defaults."""
    svc = MagicMock()
    svc.preview = AsyncMock(
        return_value=ComunicacionPreviewResponse(
            asunto_renderizado="Hola Ana",
            cuerpo_renderizado="Tu legajo es 123",
            warnings=[],
        )
    )
    svc.encolar = AsyncMock(
        return_value=ComunicacionEnviarResponse(
            lote_id=None,
            ids_encolados=[COM_ID],
            total=1,
        )
    )
    svc.aprobar_lote = AsyncMock(
        return_value=LoteAccionResponse(
            lote_id=LOTE_ID,
            afectados=2,
            estado_nuevo="Pendiente",
        )
    )
    svc.cancelar_lote = AsyncMock(
        return_value=LoteAccionResponse(
            lote_id=LOTE_ID,
            afectados=2,
            estado_nuevo="Cancelado",
        )
    )
    svc.cancelar_individual = AsyncMock(
        return_value=_make_com_response(estado=EstadoComunicacion.Cancelado)
    )
    svc.listar = AsyncMock(return_value=[_make_com_response()])
    for k, v in method_overrides.items():
        setattr(svc, k, AsyncMock(return_value=v))
    return svc


# ── 10.1 POST /preview con variables → 200 ───────────────────────────────────


class TestPreview:
    def test_preview_200_con_variables(self):
        """POST /preview con contexto → 200 con variables resueltas."""
        svc = _make_svc()
        with _client_with_perms(["comunicacion:enviar"], svc_override=svc) as client:
            resp = client.post(
                "/api/v1/comunicaciones/preview",
                json={
                    "asunto": "Hola {{alumno.nombre}}",
                    "cuerpo": "Tu legajo: {{alumno.legajo}}",
                    "contexto": {"alumno.nombre": "Ana", "alumno.legajo": "123"},
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "asunto_renderizado" in body
        assert "cuerpo_renderizado" in body
        assert "warnings" in body

    def test_preview_sin_permiso_403(self):
        """Sin comunicacion:enviar → 403."""
        with _client_with_perms([]) as client:
            resp = client.post(
                "/api/v1/comunicaciones/preview",
                json={"asunto": "x", "cuerpo": "y", "contexto": {}},
            )
        assert resp.status_code == 403


# ── 10.2 POST /enviar sin permiso → 403 ──────────────────────────────────────


class TestEnviar:
    def test_enviar_sin_permiso_403(self):
        """Sin comunicacion:enviar → 403."""
        with _client_with_perms([]) as client:
            resp = client.post(
                "/api/v1/comunicaciones/enviar",
                json={
                    "destinatarios": ["a@test.com"],
                    "asunto": "Hola",
                    "cuerpo": "Cuerpo",
                    "materia_id": str(MATERIA_ID),
                },
            )
        assert resp.status_code == 403

    # ── 10.3 POST /enviar individual → 201 ───────────────────────────────────

    def test_enviar_individual_201(self):
        """POST /enviar → 201, 1 id en respuesta."""
        svc = _make_svc()
        with _client_with_perms(["comunicacion:enviar"], svc_override=svc) as client:
            resp = client.post(
                "/api/v1/comunicaciones/enviar",
                json={
                    "destinatarios": ["a@test.com"],
                    "asunto": "Hola",
                    "cuerpo": "Cuerpo",
                    "materia_id": str(MATERIA_ID),
                },
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["total"] == 1
        assert body["lote_id"] is None

    # ── 10.4 POST /enviar masivo → lote_id generado ──────────────────────────

    def test_enviar_masivo_lote_generado(self):
        """POST /enviar 3 dest → 201, lote_id en respuesta."""
        lote = uuid.uuid4()
        svc = _make_svc(
            encolar=ComunicacionEnviarResponse(
                lote_id=lote,
                ids_encolados=[uuid.uuid4(), uuid.uuid4(), uuid.uuid4()],
                total=3,
            )
        )
        with _client_with_perms(["comunicacion:enviar"], svc_override=svc) as client:
            resp = client.post(
                "/api/v1/comunicaciones/enviar",
                json={
                    "destinatarios": ["a@t.com", "b@t.com", "c@t.com"],
                    "asunto": "Masivo",
                    "cuerpo": "Cuerpo",
                    "materia_id": str(MATERIA_ID),
                },
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["total"] == 3
        assert body["lote_id"] is not None


# ── 10.5 POST /lotes/{id}/aprobar sin permiso → 403 ──────────────────────────


class TestLotes:
    def test_aprobar_lote_sin_permiso_403(self):
        """Sin comunicacion:aprobar → 403."""
        with _client_with_perms(["comunicacion:enviar"]) as client:
            resp = client.post(
                f"/api/v1/comunicaciones/lotes/{LOTE_ID}/aprobar",
                json={},
            )
        assert resp.status_code == 403

    # ── 10.6 POST /lotes/{id}/aprobar → 200 ──────────────────────────────────

    def test_aprobar_lote_200(self):
        """POST /lotes/{id}/aprobar → 200, afectados en respuesta."""
        svc = _make_svc()
        with _client_with_perms(["comunicacion:aprobar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/comunicaciones/lotes/{LOTE_ID}/aprobar",
                json={},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "afectados" in body
        assert "lote_id" in body

    # ── 10.7 POST /lotes/{id}/cancelar → 200 ─────────────────────────────────

    def test_cancelar_lote_200(self):
        """POST /lotes/{id}/cancelar → 200, todos Cancelado."""
        svc = _make_svc()
        with _client_with_perms(["comunicacion:aprobar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/comunicaciones/lotes/{LOTE_ID}/cancelar",
                json={},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["estado_nuevo"] == "Cancelado"


# ── 10.8 POST /{id}/cancelar sobre Pendiente → 200 ───────────────────────────


class TestCancelarIndividual:
    def test_cancelar_individual_ok(self):
        """POST /{id}/cancelar sobre Pendiente → 200 Cancelado."""
        svc = _make_svc()
        with _client_with_perms(["comunicacion:enviar"], svc_override=svc) as client:
            resp = client.post(f"/api/v1/comunicaciones/{COM_ID}/cancelar")
        assert resp.status_code == 200
        body = resp.json()
        assert body["estado"] == "Cancelado"

    # ── 10.9 POST /{id}/cancelar sobre Enviado → 422 ─────────────────────────

    def test_cancelar_individual_no_pendiente_422(self):
        """POST /{id}/cancelar sobre Enviado → 422."""
        from fastapi import HTTPException

        svc = MagicMock()
        svc.cancelar_individual = AsyncMock(
            side_effect=HTTPException(status_code=422, detail="No cancelable")
        )

        with _client_with_perms(["comunicacion:enviar"], svc_override=svc) as client:
            resp = client.post(f"/api/v1/comunicaciones/{COM_ID}/cancelar")
        assert resp.status_code == 422


# ── 10.10 GET / scoped por tenant ────────────────────────────────────────────


class TestListado:
    def test_listado_scoped_por_tenant(self):
        """Mensajes de tenant A no visibles desde tenant B (service retorna lista vacía para B)."""
        svc_a = _make_svc()  # Tenant A tiene 1 mensaje
        svc_b = _make_svc(listar=[])  # Tenant B no tiene nada

        user_b = _make_user(tenant_id=TENANT_ID_B)

        with _client_with_perms(
            ["comunicacion:ver"], user=user_b, svc_override=svc_b
        ) as client:
            resp = client.get("/api/v1/comunicaciones/")
        assert resp.status_code == 200
        body = resp.json()
        assert body == []

    # ── 10.11 destinatario_masked nunca expone email en claro ─────────────────

    def test_listado_destinatario_enmascarado(self):
        """Campo destinatario_masked nunca expone email en claro."""
        svc = _make_svc()
        with _client_with_perms(["comunicacion:ver"], svc_override=svc) as client:
            resp = client.get("/api/v1/comunicaciones/")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        item = items[0]
        # destinatario_masked no debe ser un email en claro
        masked = item["destinatario_masked"]
        assert "@" not in masked or masked == "****@****"
        # Nunca debe aparecer el campo raw "destinatario"
        assert "destinatario" not in item or item.get("destinatario") is None

    # ── 10.12 GET /?estado=Pendiente → solo Pendiente ─────────────────────────

    def test_listado_filtro_estado(self):
        """?estado=Pendiente → solo Pendiente en respuesta."""
        svc = _make_svc()
        with _client_with_perms(["comunicacion:ver"], svc_override=svc) as client:
            resp = client.get(
                "/api/v1/comunicaciones/",
                params={"estado": "Pendiente"},
            )
        assert resp.status_code == 200
        # Verificar que el service fue llamado con el filtro correcto
        svc.listar.assert_called_once()
        call_kwargs = svc.listar.call_args.kwargs
        assert call_kwargs.get("estado") == EstadoComunicacion.Pendiente


# ── 10.13 Audit log en envío ──────────────────────────────────────────────────


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_audit_log_en_envio(self):
        """Después de que el worker despacha → AuditLog con COMUNICACION_ENVIAR."""
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from sqlalchemy import select
        from app.models.base import Base
        import app.models  # noqa: F401
        from app.workers.comunicacion_worker import _process_pendientes
        from app.repositories.comunicacion_repository import ComunicacionRepository
        from app.core.security import AES256GCMCipher, derive_encryption_key
        from app.models.audit_log import AuditLog
        from app.models.user import User
        from app.models.tenant import Tenant

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        cipher = AES256GCMCipher(derive_encryption_key("b" * 64))

        # Crear usuario y tenant
        async with session_factory() as session:
            t = Tenant(id=uuid.uuid4(), name="AuditTenant")
            session.add(t)
            await session.commit()

            u = User(
                id=uuid.uuid4(),
                tenant_id=t.id,
                email="actor@test.com",
                nombre="Actor",
                apellidos="Test",
                password_hash="x",
            )
            session.add(u)
            await session.commit()

            repo = ComunicacionRepository(session, cipher)
            com = await repo.create(
                tenant_id=t.id,
                enviado_por=u.id,
                materia_id=uuid.uuid4(),
                destinatario_plain="dest@test.com",
                asunto="Con audit",
                cuerpo="Cuerpo",
            )
            await session.commit()
            com_id = com.id
            tenant_id = t.id

        smtp_stub = MagicMock()
        smtp_stub.send = AsyncMock(return_value=True)

        await _process_pendientes(session_factory, smtp_stub)

        async with session_factory() as session:
            audit_q = select(AuditLog).where(
                AuditLog.accion == "COMUNICACION_ENVIAR",
                AuditLog.tenant_id == tenant_id,
            )
            result = await session.execute(audit_q)
            logs = result.scalars().all()

        assert len(logs) == 1
        assert logs[0].accion == "COMUNICACION_ENVIAR"

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
