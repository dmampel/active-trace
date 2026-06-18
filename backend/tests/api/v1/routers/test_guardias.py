"""Tests del router de guardias (C-13, Tareas 8.1–8.8).

Patrón: TestClient + mocked get_current_user + patched RbacRepository.
Los servicios se mockean para aislar la lógica del router de la DB.
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.models.guardia import EstadoGuardia
from app.schemas.guardia import GuardiaResponse

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
TUTOR_ID = uuid.uuid4()
COORDINADOR_ID = uuid.uuid4()
ASIGNACION_TUTOR = uuid.uuid4()
ASIGNACION_OTRO_TUTOR = uuid.uuid4()
MATERIA_ID = uuid.uuid4()
GUARDIA_ID = uuid.uuid4()
HOY = date.today()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(roles=None, user_id=None, tenant_id=None):
    user = MagicMock()
    user.id = user_id or TUTOR_ID
    user.tenant_id = tenant_id or TENANT_A
    user.roles = roles or ["TUTOR"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


def _make_guardia_response(
    guardia_id=None, asignacion_id=None, materia_id=None, tenant_id=None
) -> GuardiaResponse:
    return GuardiaResponse(
        id=guardia_id or GUARDIA_ID,
        tenant_id=tenant_id or TENANT_A,
        asignacion_id=asignacion_id or ASIGNACION_TUTOR,
        materia_id=materia_id or MATERIA_ID,
        carrera_id=None,
        cohorte_id=None,
        dia=HOY,
        horario="14:00–14:45",
        estado=EstadoGuardia.Pendiente,
        comentarios=None,
    )


@contextmanager
def _client_with_perms(perms: list[str], user=None, svc_override=None):
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db

    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override:
            import app.api.v1.routers.guardias as router_mod
            app.dependency_overrides[router_mod._get_guardia_service] = (
                lambda: svc_override
            )
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override:
                import app.api.v1.routers.guardias as router_mod
                app.dependency_overrides.pop(router_mod._get_guardia_service, None)


def _make_svc(**overrides):
    svc = MagicMock()
    svc.registrar = AsyncMock(return_value=_make_guardia_response())
    svc.listar = AsyncMock(return_value=[_make_guardia_response()])
    # exportar_csv es un async generator
    async def _default_csv_gen(*args, **kwargs):
        yield "tutor,materia,carrera,cohorte,dia,horario,estado,comentarios,creada_at\n"
        yield f"{ASIGNACION_TUTOR},{MATERIA_ID},,,{HOY},14:00-14:45,Pendiente,,\n"
    svc.exportar_csv = _default_csv_gen
    for k, v in overrides.items():
        if k != "exportar_csv":
            setattr(svc, k, AsyncMock(return_value=v))
        else:
            setattr(svc, k, v)
    return svc


# ── 8.1 TUTOR registra guardia → 201; asignacion_id del JWT, no del body ──────


class TestRegistrarGuardia:
    def test_tutor_registra_guardia_201(self):
        """TUTOR POST /api/guardias → 201; asignacion_id del query param (JWT context)."""
        tutor = _make_user(roles=["TUTOR"])
        svc = _make_svc()
        with _client_with_perms(["guardias:registrar"], user=tutor, svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/guardias/?asignacion_id={ASIGNACION_TUTOR}",
                json={
                    "materia_id": str(MATERIA_ID),
                    "dia": str(HOY),
                    "horario": "14:00–14:45",
                },
            )
        assert resp.status_code == 201
        body = resp.json()
        # asignacion_id viene del param, nunca del body
        assert body["asignacion_id"] == str(ASIGNACION_TUTOR)
        assert body["tenant_id"] == str(TENANT_A)

    def test_asignacion_id_no_en_body(self):
        """Body sin asignacion_id no provoca error — se ignora si estuviera."""
        tutor = _make_user(roles=["TUTOR"])
        svc = _make_svc()
        with _client_with_perms(["guardias:registrar"], user=tutor, svc_override=svc) as client:
            # Si alguien intentara pasar asignacion_id en el body, extra='forbid' lo rechaza
            resp = client.post(
                f"/api/v1/guardias/?asignacion_id={ASIGNACION_TUTOR}",
                json={
                    "materia_id": str(MATERIA_ID),
                    "dia": str(HOY),
                    "horario": "14:00–14:45",
                    "asignacion_id": str(uuid.uuid4()),  # campo extra → 422
                },
            )
        assert resp.status_code == 422  # extra='forbid' rechaza el campo

    # ── 8.2 PROFESOR intenta POST → 403 ──────────────────────────────────────

    def test_profesor_registrar_guardia_403(self):
        """PROFESOR POST /api/guardias → HTTP 403."""
        profesor = _make_user(roles=["PROFESOR"])
        with _client_with_perms([], user=profesor) as client:
            resp = client.post(
                f"/api/v1/guardias/?asignacion_id={ASIGNACION_TUTOR}",
                json={
                    "materia_id": str(MATERIA_ID),
                    "dia": str(HOY),
                    "horario": "14:00–14:45",
                },
            )
        assert resp.status_code == 403


# ── 8.3 TUTOR GET /guardias → solo sus propias guardias ──────────────────────


class TestListarGuardias:
    def test_tutor_solo_ve_sus_guardias(self):
        """TUTOR GET /api/guardias?asignacion_id=X → solo las suyas."""
        guardia_tutor = _make_guardia_response(asignacion_id=ASIGNACION_TUTOR)
        svc = _make_svc(listar=[guardia_tutor])
        tutor = _make_user(roles=["TUTOR"])
        with _client_with_perms(
            ["guardias:consultar"], user=tutor, svc_override=svc
        ) as client:
            resp = client.get(f"/api/v1/guardias/?asignacion_id={ASIGNACION_TUTOR}")
        assert resp.status_code == 200
        guardias = resp.json()
        assert len(guardias) == 1
        assert guardias[0]["asignacion_id"] == str(ASIGNACION_TUTOR)

    # ── 8.4 COORDINADOR ve todas las guardias del tenant ─────────────────────

    def test_coordinador_ve_todas_las_guardias(self):
        """COORDINADOR GET /api/guardias → todas las guardias del tenant."""
        g1 = _make_guardia_response(guardia_id=uuid.uuid4(), asignacion_id=ASIGNACION_TUTOR)
        g2 = _make_guardia_response(guardia_id=uuid.uuid4(), asignacion_id=ASIGNACION_OTRO_TUTOR)
        svc = _make_svc(listar=[g1, g2])
        coord = _make_user(roles=["COORDINADOR"])
        with _client_with_perms(
            ["guardias:consultar"], user=coord, svc_override=svc
        ) as client:
            resp = client.get("/api/v1/guardias/")
        assert resp.status_code == 200
        guardias = resp.json()
        assert len(guardias) == 2

    # ── 8.5 Filtro por materia_id retorna solo guardias de esa materia ────────

    def test_filtro_materia_id_retorna_solo_esa_materia(self):
        """GET /api/guardias?materia_id=X → solo guardias de esa materia."""
        guardia_materia = _make_guardia_response(materia_id=MATERIA_ID)
        svc = _make_svc(listar=[guardia_materia])
        coord = _make_user(roles=["COORDINADOR"])
        with _client_with_perms(
            ["guardias:consultar"], user=coord, svc_override=svc
        ) as client:
            resp = client.get(f"/api/v1/guardias/?materia_id={MATERIA_ID}")
        assert resp.status_code == 200
        guardias = resp.json()
        assert all(g["materia_id"] == str(MATERIA_ID) for g in guardias)


# ── 8.6 TUTOR GET /export → 403 ───────────────────────────────────────────────


class TestExportarGuardias:
    def test_tutor_export_403(self):
        """TUTOR GET /api/guardias/export → HTTP 403."""
        tutor = _make_user(roles=["TUTOR"])
        # TUTOR tiene guardias:consultar pero NO guardias:exportar
        with _client_with_perms(["guardias:consultar"], user=tutor) as client:
            resp = client.get("/api/v1/guardias/export")
        assert resp.status_code == 403

    # ── 8.7 COORDINADOR GET /export → CSV con headers correctos ──────────────

    def test_coordinador_export_csv_headers_correctos(self):
        """COORDINADOR GET /api/guardias/export → CSV con headers correctos."""
        svc = _make_svc()
        coord = _make_user(roles=["COORDINADOR"])
        with _client_with_perms(
            ["guardias:exportar"], user=coord, svc_override=svc
        ) as client:
            resp = client.get("/api/v1/guardias/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        content = resp.text
        assert "tutor" in content
        assert "materia" in content
        assert "horario" in content
        assert "estado" in content

    # ── 8.8 Aislamiento tenant en guardias ────────────────────────────────────

    def test_aislamiento_tenant_guardias(self):
        """Usuario tenant A no ve guardias de tenant B."""
        guardia_a = _make_guardia_response(tenant_id=TENANT_A)
        svc = _make_svc(listar=[guardia_a])
        user_a = _make_user(tenant_id=TENANT_A)
        with _client_with_perms(
            ["guardias:consultar"], user=user_a, svc_override=svc
        ) as client:
            resp = client.get("/api/v1/guardias/")
        assert resp.status_code == 200
        guardias = resp.json()
        # Todas las guardias retornadas son del tenant A
        for g in guardias:
            assert g["tenant_id"] == str(TENANT_A)
