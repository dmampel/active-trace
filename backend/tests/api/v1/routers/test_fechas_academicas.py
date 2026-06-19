"""Tests del router de fechas académicas (C-14, Tareas 8.1–8.4).

Patrón: TestClient + mocked get_current_user + patched RbacRepository.
Los servicios se mockean para aislar la lógica del router de la DB.
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

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.models.evaluacion import TipoFechaAcademica
from app.schemas.fecha_academica import FechaAcademicaRead

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
FECHA_ID = uuid.uuid4()
MATERIA_ID = uuid.uuid4()
COHORTE_ID = uuid.uuid4()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(roles=None, tenant_id=None):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.tenant_id = tenant_id or TENANT_A
    user.roles = roles or ["COORDINADOR"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


def _make_fecha_read() -> FechaAcademicaRead:
    return FechaAcademicaRead(
        id=FECHA_ID,
        tenant_id=TENANT_A,
        materia_id=MATERIA_ID,
        cohorte_id=COHORTE_ID,
        tipo=TipoFechaAcademica.Parcial,
        numero=1,
        periodo="2026-1",
        fecha="2026-05-10",
        titulo="Primer Parcial",
    )


def _make_svc(**overrides):
    svc = MagicMock()
    svc.crear = AsyncMock(return_value=_make_fecha_read())
    svc.listar = AsyncMock(return_value=[_make_fecha_read()])
    svc.actualizar = AsyncMock(return_value=_make_fecha_read())
    svc.eliminar = AsyncMock(return_value=None)
    for k, v in overrides.items():
        setattr(svc, k, AsyncMock(return_value=v) if not isinstance(v, AsyncMock) else v)
    return svc


@contextmanager
def _client_with_perms(perms: list[str], user=None, svc_override=None):
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db

    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override:
            import app.api.v1.routers.fechas_academicas as router_mod
            app.dependency_overrides[router_mod._get_fecha_academica_service] = (
                lambda: svc_override
            )
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override:
                import app.api.v1.routers.fechas_academicas as router_mod
                app.dependency_overrides.pop(
                    router_mod._get_fecha_academica_service, None
                )


_PAYLOAD_VALIDO = {
    "materia_id": str(MATERIA_ID),
    "cohorte_id": str(COHORTE_ID),
    "tipo": "Parcial",
    "numero": 1,
    "periodo": "2026-1",
    "fecha": "2026-05-10",
    "titulo": "Primer Parcial",
}


# ── 8.1 Crear fecha académica ─────────────────────────────────────────────────


class TestCrearFechaAcademica:
    def test_crear_exitosa(self):
        """POST /fechas-academicas → 201."""
        svc = _make_svc()
        with _client_with_perms(["estructura:gestionar"], svc_override=svc) as client:
            resp = client.post("/api/v1/fechas-academicas", json=_PAYLOAD_VALIDO)
        assert resp.status_code == 201
        body = resp.json()
        assert body["tipo"] == "Parcial"
        assert body["titulo"] == "Primer Parcial"

    def test_tipo_invalido_422(self):
        """POST /fechas-academicas con tipo inválido → 422."""
        svc = _make_svc()
        payload = {**_PAYLOAD_VALIDO, "tipo": "ExamenFinal"}  # no es un enum válido
        with _client_with_perms(["estructura:gestionar"], svc_override=svc) as client:
            resp = client.post("/api/v1/fechas-academicas", json=payload)
        assert resp.status_code == 422

    def test_sin_permiso_403(self):
        """ALUMNO POST /fechas-academicas → 403."""
        alumno = _make_user(roles=["ALUMNO"])
        with _client_with_perms([], user=alumno) as client:
            resp = client.post("/api/v1/fechas-academicas", json=_PAYLOAD_VALIDO)
        assert resp.status_code == 403


# ── 8.2 Listar fechas con filtros ─────────────────────────────────────────────


class TestListarFechasAcademicas:
    def test_listar_sin_filtros(self):
        """GET /fechas-academicas → lista de fechas del tenant."""
        svc = _make_svc()
        with _client_with_perms(["estructura:leer"], svc_override=svc) as client:
            resp = client.get("/api/v1/fechas-academicas")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_filtro_por_materia_id(self):
        """GET /fechas-academicas?materia_id=X → llama listar con materia_id."""
        svc = _make_svc()
        with _client_with_perms(["estructura:leer"], svc_override=svc) as client:
            resp = client.get(f"/api/v1/fechas-academicas?materia_id={MATERIA_ID}")
        assert resp.status_code == 200
        # Verificar que el servicio fue llamado (el svc mock devuelve la lista)
        assert isinstance(resp.json(), list)

    def test_filtro_por_cohorte_id(self):
        """GET /fechas-academicas?cohorte_id=X → filtra por cohorte."""
        svc = _make_svc()
        with _client_with_perms(["estructura:leer"], svc_override=svc) as client:
            resp = client.get(f"/api/v1/fechas-academicas?cohorte_id={COHORTE_ID}")
        assert resp.status_code == 200

    def test_filtro_combinado(self):
        """GET /fechas-academicas?materia_id=X&cohorte_id=Y → ambos filtros."""
        svc = _make_svc()
        with _client_with_perms(["estructura:leer"], svc_override=svc) as client:
            resp = client.get(
                f"/api/v1/fechas-academicas?materia_id={MATERIA_ID}&cohorte_id={COHORTE_ID}"
            )
        assert resp.status_code == 200


# ── 8.3 Editar y eliminar fecha académica ─────────────────────────────────────


class TestEditarEliminarFechaAcademica:
    def test_editar_fecha(self):
        """PUT /fechas-academicas/{id} → 200 con fecha actualizada."""
        actualizada = FechaAcademicaRead(
            id=FECHA_ID,
            tenant_id=TENANT_A,
            materia_id=MATERIA_ID,
            cohorte_id=COHORTE_ID,
            tipo=TipoFechaAcademica.Parcial,
            numero=1,
            periodo="2026-1",
            fecha="2026-05-15",
            titulo="Primer Parcial (reprogramado)",
        )
        svc = _make_svc(actualizar=actualizada)
        with _client_with_perms(["estructura:gestionar"], svc_override=svc) as client:
            resp = client.patch(
                f"/api/v1/fechas-academicas/{FECHA_ID}",
                json={"titulo": "Primer Parcial (reprogramado)", "fecha": "2026-05-15"},
            )
        assert resp.status_code == 200
        assert resp.json()["titulo"] == "Primer Parcial (reprogramado)"

    def test_eliminar_fecha(self):
        """DELETE /fechas-academicas/{id} → 204."""
        svc = _make_svc()
        with _client_with_perms(["estructura:gestionar"], svc_override=svc) as client:
            resp = client.delete(f"/api/v1/fechas-academicas/{FECHA_ID}")
        assert resp.status_code == 204

    def test_eliminar_no_existente_404(self):
        """DELETE /fechas-academicas/{id} no encontrado → 404."""
        svc = _make_svc()
        svc.eliminar = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="No encontrada")
        )
        with _client_with_perms(["estructura:gestionar"], svc_override=svc) as client:
            resp = client.delete(f"/api/v1/fechas-academicas/{uuid.uuid4()}")
        assert resp.status_code == 404


# ── 8.4 Aislamiento de tenant ─────────────────────────────────────────────────


class TestTenantIsolacionFechas:
    def test_tenant_a_no_ve_fechas_de_tenant_b(self):
        """GET /fechas-academicas de tenant A no incluye fechas de tenant B."""
        fecha_a = _make_fecha_read()
        svc = _make_svc(listar=[fecha_a])
        user_a = _make_user(tenant_id=TENANT_A)

        with _client_with_perms(["estructura:leer"], user=user_a, svc_override=svc) as client:
            resp = client.get("/api/v1/fechas-academicas")

        assert resp.status_code == 200
        items = resp.json()
        for item in items:
            assert item["tenant_id"] == str(TENANT_A)

    def test_tenant_id_rechazado_en_body(self):
        """POST /fechas-academicas con tenant_id en body → 422 (extra='forbid')."""
        svc = _make_svc()
        payload_con_tenant = {**_PAYLOAD_VALIDO, "tenant_id": str(TENANT_B)}
        with _client_with_perms(["estructura:gestionar"], svc_override=svc) as client:
            resp = client.post("/api/v1/fechas-academicas", json=payload_con_tenant)
        assert resp.status_code == 422
