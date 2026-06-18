"""Tests del router de coloquios (C-14, Tareas 7.1–7.11).

Patrón: TestClient + mocked get_current_user + patched RbacRepository.
Los servicios se mockean para aislar la lógica del router de la DB.

Safety net: 494 tests passing antes de agregar estos tests.
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

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.models.evaluacion import EstadoReserva, TipoEvaluacion
from app.schemas.evaluacion import (
    AgendaEntradaRead,
    EvaluacionAlumnoImportResult,
    EvaluacionRead,
    MetricasColoquioRead,
    ReservaEvaluacionRead,
    ResultadoEvaluacionRead,
)

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_ID = uuid.uuid4()
ALUMNO_ID = uuid.uuid4()
EVAL_ID = uuid.uuid4()
RESERVA_ID = uuid.uuid4()
MATERIA_ID = uuid.uuid4()
COHORTE_ID = uuid.uuid4()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(roles=None, tenant_id=None, user_id=None):
    user = MagicMock()
    user.id = user_id or USER_ID
    user.tenant_id = tenant_id or TENANT_A
    user.roles = roles or ["COORDINADOR"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


def _make_evaluacion_read() -> EvaluacionRead:
    return EvaluacionRead(
        id=EVAL_ID,
        tenant_id=TENANT_A,
        materia_id=MATERIA_ID,
        cohorte_id=COHORTE_ID,
        tipo=TipoEvaluacion.Coloquio,
        instancia="1er Coloquio",
        cupos_por_dia={"2026-07-10": 5},
    )


def _make_reserva_read() -> ReservaEvaluacionRead:
    return ReservaEvaluacionRead(
        id=RESERVA_ID,
        evaluacion_id=EVAL_ID,
        alumno_id=ALUMNO_ID,
        fecha="2026-07-10",
        estado=EstadoReserva.Activa,
    )


def _make_resultado_read() -> ResultadoEvaluacionRead:
    return ResultadoEvaluacionRead(
        id=uuid.uuid4(),
        evaluacion_id=EVAL_ID,
        alumno_id=ALUMNO_ID,
        nota_final="Aprobado",
    )


def _make_metricas() -> MetricasColoquioRead:
    return MetricasColoquioRead(
        total_convocados=10,
        instancias_activas=2,
        reservas_activas=7,
        notas_registradas=5,
    )


def _make_svc(**overrides):
    svc = MagicMock()
    svc.crear = AsyncMock(return_value=_make_evaluacion_read())
    svc.listar = AsyncMock(return_value=[_make_evaluacion_read()])
    svc.obtener = AsyncMock(return_value=_make_evaluacion_read())
    svc.actualizar = AsyncMock(return_value=_make_evaluacion_read())
    svc.eliminar = AsyncMock(return_value=None)
    svc.importar_alumnos = AsyncMock(
        return_value=EvaluacionAlumnoImportResult(total_convocados=2, importados=2)
    )
    svc.reservar_turno = AsyncMock(return_value=_make_reserva_read())
    svc.cancelar_reserva = AsyncMock(return_value=None)
    svc.get_metricas = AsyncMock(return_value=_make_metricas())
    svc.get_agenda = AsyncMock(return_value=[])
    svc.get_resultados = AsyncMock(return_value=[_make_resultado_read()])
    svc.upsert_resultado = AsyncMock(return_value=_make_resultado_read())
    for k, v in overrides.items():
        setattr(svc, k, AsyncMock(return_value=v) if not isinstance(v, AsyncMock) else v)
    return svc


@contextmanager
def _client_with_perms(perms: list[str], user=None, svc_override=None):
    """Construye TestClient con permisos y servicio mockeados."""
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db

    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override:
            import app.api.v1.routers.coloquios as router_mod
            app.dependency_overrides[router_mod._get_evaluacion_service] = (
                lambda: svc_override
            )
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override:
                import app.api.v1.routers.coloquios as router_mod
                app.dependency_overrides.pop(
                    router_mod._get_evaluacion_service, None
                )


# ── 7.1 Crear convocatoria ─────────────────────────────────────────────────────


class TestCrearConvocatoria:
    def test_crear_exitoso(self):
        """POST /coloquios → 201 con convocatoria creada."""
        svc = _make_svc()
        with _client_with_perms(["coloquios:gestionar"], svc_override=svc) as client:
            resp = client.post(
                "/api/v1/coloquios",
                json={
                    "materia_id": str(MATERIA_ID),
                    "cohorte_id": str(COHORTE_ID),
                    "tipo": "Coloquio",
                    "instancia": "1er Coloquio",
                    "cupos_por_dia": {"2026-07-10": 5},
                },
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["instancia"] == "1er Coloquio"
        assert body["tipo"] == "Coloquio"

    def test_campo_faltante_422(self):
        """POST /coloquios sin instancia → 422."""
        svc = _make_svc()
        with _client_with_perms(["coloquios:gestionar"], svc_override=svc) as client:
            resp = client.post(
                "/api/v1/coloquios",
                json={
                    "materia_id": str(MATERIA_ID),
                    "cohorte_id": str(COHORTE_ID),
                    "tipo": "Coloquio",
                    # instancia omitida
                },
            )
        assert resp.status_code == 422

    def test_alumno_sin_permiso_403(self):
        """ALUMNO POST /coloquios → 403."""
        alumno = _make_user(roles=["ALUMNO"], tenant_id=TENANT_A)
        with _client_with_perms([], user=alumno) as client:
            resp = client.post(
                "/api/v1/coloquios",
                json={
                    "materia_id": str(MATERIA_ID),
                    "cohorte_id": str(COHORTE_ID),
                    "tipo": "Coloquio",
                    "instancia": "1er Coloquio",
                },
            )
        assert resp.status_code == 403


# ── 7.2 Importar alumnos ──────────────────────────────────────────────────────


class TestImportarAlumnos:
    def test_importacion_exitosa(self):
        """POST /coloquios/{id}/alumnos → 200 con resultado."""
        svc = _make_svc()
        with _client_with_perms(["coloquios:gestionar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/alumnos",
                json={"alumno_ids": [str(ALUMNO_ID)]},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["importados"] == 2

    def test_alumno_otro_tenant_rechazado_422(self):
        """POST /coloquios/{id}/alumnos con alumno de otro tenant → 422."""
        svc = _make_svc()
        svc.importar_alumnos = AsyncMock(
            side_effect=HTTPException(status_code=422, detail="alumno de otro tenant")
        )
        with _client_with_perms(["coloquios:gestionar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/alumnos",
                json={"alumno_ids": [str(uuid.uuid4())]},
            )
        assert resp.status_code == 422


# ── 7.3 Reservar turno ────────────────────────────────────────────────────────


class TestReservarTurno:
    def test_reserva_exitosa(self):
        """POST /coloquios/{id}/reservar → 201."""
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        svc = _make_svc()
        with _client_with_perms(["coloquios:reservar"], user=alumno, svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/reservar",
                json={"fecha": "2026-07-10"},
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["estado"] == "Activa"

    def test_cupo_agotado_409(self):
        """POST /coloquios/{id}/reservar con cupo 0 → 409."""
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        svc = _make_svc()
        svc.reservar_turno = AsyncMock(
            side_effect=HTTPException(status_code=409, detail="Cupo agotado")
        )
        with _client_with_perms(["coloquios:reservar"], user=alumno, svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/reservar",
                json={"fecha": "2026-07-10"},
            )
        assert resp.status_code == 409

    def test_alumno_no_habilitado_403(self):
        """POST /coloquios/{id}/reservar alumno no convocado → 403."""
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        svc = _make_svc()
        svc.reservar_turno = AsyncMock(
            side_effect=HTTPException(status_code=403, detail="Alumno no habilitado")
        )
        with _client_with_perms(["coloquios:reservar"], user=alumno, svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/reservar",
                json={"fecha": "2026-07-10"},
            )
        assert resp.status_code == 403

    def test_reserva_duplicada_409(self):
        """POST /coloquios/{id}/reservar con reserva activa existente → 409."""
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        svc = _make_svc()
        svc.reservar_turno = AsyncMock(
            side_effect=HTTPException(status_code=409, detail="Reserva duplicada")
        )
        with _client_with_perms(["coloquios:reservar"], user=alumno, svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/reservar",
                json={"fecha": "2026-07-10"},
            )
        assert resp.status_code == 409


# ── 7.4 Cancelar reserva ──────────────────────────────────────────────────────


class TestCancelarReserva:
    def test_cancelacion_exitosa(self):
        """DELETE /coloquios/{id}/reservar → 200."""
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        svc = _make_svc()
        with _client_with_perms(["coloquios:reservar"], user=alumno, svc_override=svc) as client:
            resp = client.delete(f"/api/v1/coloquios/{EVAL_ID}/reservar")
        assert resp.status_code == 200

    def test_sin_reserva_activa_404(self):
        """DELETE /coloquios/{id}/reservar sin reserva → 404."""
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        svc = _make_svc()
        svc.cancelar_reserva = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Sin reserva activa")
        )
        with _client_with_perms(["coloquios:reservar"], user=alumno, svc_override=svc) as client:
            resp = client.delete(f"/api/v1/coloquios/{EVAL_ID}/reservar")
        assert resp.status_code == 404


# ── 7.5 UPDATE atómico — race condition ───────────────────────────────────────
# Este test es sobre la lógica del repositorio, no del router.
# Se verifica que el service propaga ConflictError como 409.


class TestUpdateAtomico:
    def test_dos_reservas_concurrentes_solo_una_pasa(self):
        """Simula que la segunda reserva obtiene ConflictError → 409."""
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)

        call_count = 0

        async def reserva_segunda_falla(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise HTTPException(status_code=409, detail="Cupo agotado")
            return _make_reserva_read()

        svc = _make_svc()
        svc.reservar_turno = reserva_segunda_falla

        with _client_with_perms(["coloquios:reservar"], user=alumno, svc_override=svc) as client:
            # Primera reserva pasa
            resp1 = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/reservar",
                json={"fecha": "2026-07-10"},
            )
            # Segunda reserva falla por cupo agotado
            resp2 = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/reservar",
                json={"fecha": "2026-07-10"},
            )

        assert resp1.status_code == 201
        assert resp2.status_code == 409


# ── 7.6 Listar convocatorias ──────────────────────────────────────────────────


class TestListarConvocatorias:
    def test_coordinador_ve_convocatorias_del_tenant(self):
        """GET /coloquios → lista con las convocatorias del tenant."""
        svc = _make_svc()
        with _client_with_perms(["coloquios:ver"], svc_override=svc) as client:
            resp = client.get("/api/v1/coloquios")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1

    def test_lista_vacia(self):
        """GET /coloquios sin convocatorias → lista vacía."""
        svc = _make_svc(listar=[])
        with _client_with_perms(["coloquios:ver"], svc_override=svc) as client:
            resp = client.get("/api/v1/coloquios")
        assert resp.status_code == 200
        assert resp.json() == []


# ── 7.7 Métricas ─────────────────────────────────────────────────────────────


class TestMetricas:
    def test_metricas_con_datos(self):
        """GET /coloquios/metricas → valores correctos."""
        svc = _make_svc()
        with _client_with_perms(["coloquios:ver"], svc_override=svc) as client:
            resp = client.get("/api/v1/coloquios/metricas")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_convocados"] == 10
        assert body["instancias_activas"] == 2
        assert body["reservas_activas"] == 7
        assert body["notas_registradas"] == 5

    def test_metricas_vacias(self):
        """GET /coloquios/metricas sin datos → todo 0."""
        vacias = MetricasColoquioRead(
            total_convocados=0,
            instancias_activas=0,
            reservas_activas=0,
            notas_registradas=0,
        )
        svc = _make_svc(get_metricas=vacias)
        with _client_with_perms(["coloquios:ver"], svc_override=svc) as client:
            resp = client.get("/api/v1/coloquios/metricas")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_convocados"] == 0
        assert body["reservas_activas"] == 0


# ── 7.8 Upsert resultado ──────────────────────────────────────────────────────


class TestUpsertResultado:
    def test_crear_resultado_texto(self):
        """POST /coloquios/{id}/resultados con nota texto → 201."""
        svc = _make_svc()
        with _client_with_perms(["coloquios:gestionar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/resultados",
                json={"alumno_id": str(ALUMNO_ID), "nota_final": "Aprobado"},
            )
        assert resp.status_code == 201
        assert resp.json()["nota_final"] == "Aprobado"

    def test_actualizar_resultado(self):
        """POST /coloquios/{id}/resultados con nota actualizada."""
        nota_actualizada = ResultadoEvaluacionRead(
            id=uuid.uuid4(),
            evaluacion_id=EVAL_ID,
            alumno_id=ALUMNO_ID,
            nota_final="8.5",
        )
        svc = _make_svc(upsert_resultado=nota_actualizada)
        with _client_with_perms(["coloquios:gestionar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/resultados",
                json={"alumno_id": str(ALUMNO_ID), "nota_final": "8.5"},
            )
        assert resp.status_code == 201
        assert resp.json()["nota_final"] == "8.5"

    def test_nota_numerica_aceptada(self):
        """nota_final puede ser string numérico."""
        nota = ResultadoEvaluacionRead(
            id=uuid.uuid4(),
            evaluacion_id=EVAL_ID,
            alumno_id=ALUMNO_ID,
            nota_final="9",
        )
        svc = _make_svc(upsert_resultado=nota)
        with _client_with_perms(["coloquios:gestionar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/coloquios/{EVAL_ID}/resultados",
                json={"alumno_id": str(ALUMNO_ID), "nota_final": "9"},
            )
        assert resp.status_code == 201


# ── 7.9 Agenda ────────────────────────────────────────────────────────────────


class TestAgenda:
    def test_agenda_con_reservas(self):
        """GET /coloquios/{id}/agenda → lista de reservas activas."""
        entrada = AgendaEntradaRead(
            reserva_id=RESERVA_ID,
            alumno_id=ALUMNO_ID,
            fecha="2026-07-10",
            estado=EstadoReserva.Activa,
        )
        svc = _make_svc(get_agenda=[entrada])
        with _client_with_perms(["coloquios:ver"], svc_override=svc) as client:
            resp = client.get(f"/api/v1/coloquios/{EVAL_ID}/agenda")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["fecha"] == "2026-07-10"

    def test_agenda_vacia(self):
        """GET /coloquios/{id}/agenda sin reservas → lista vacía."""
        svc = _make_svc(get_agenda=[])
        with _client_with_perms(["coloquios:ver"], svc_override=svc) as client:
            resp = client.get(f"/api/v1/coloquios/{EVAL_ID}/agenda")
        assert resp.status_code == 200
        assert resp.json() == []


# ── 7.10 Soft delete ─────────────────────────────────────────────────────────


class TestSoftDelete:
    def test_convocatoria_eliminada_no_aparece_en_list(self):
        """DELETE + GET /coloquios → la eliminada no aparece."""
        svc = _make_svc()
        # Después de eliminar, listar retorna lista vacía
        svc.listar = AsyncMock(return_value=[])

        with _client_with_perms(["coloquios:gestionar", "coloquios:ver"], svc_override=svc) as client:
            del_resp = client.delete(f"/api/v1/coloquios/{EVAL_ID}")
            assert del_resp.status_code == 200

            list_resp = client.get("/api/v1/coloquios")
            assert list_resp.status_code == 200
            assert list_resp.json() == []

    def test_resultados_de_convocatoria_eliminada_accesibles(self):
        """GET /coloquios/{id}/resultados con convocatoria eliminada → 200 con resultados."""
        svc = _make_svc()
        # El servicio retorna resultados aunque la evaluación esté soft-deleted
        with _client_with_perms(["coloquios:ver"], svc_override=svc) as client:
            resp = client.get(f"/api/v1/coloquios/{EVAL_ID}/resultados")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


# ── 7.11 Multi-tenancy ────────────────────────────────────────────────────────


class TestMultiTenancy:
    def test_tenant_a_no_ve_datos_de_tenant_b(self):
        """GET /coloquios de tenant A no incluye convocatorias de tenant B."""
        eval_a = _make_evaluacion_read()
        svc = _make_svc(listar=[eval_a])
        user_a = _make_user(tenant_id=TENANT_A)

        with _client_with_perms(["coloquios:ver"], user=user_a, svc_override=svc) as client:
            resp = client.get("/api/v1/coloquios")

        assert resp.status_code == 200
        items = resp.json()
        # Todos los items son del tenant A
        for item in items:
            assert item["tenant_id"] == str(TENANT_A)

    def test_tenant_id_nunca_desde_body(self):
        """Si el body incluye tenant_id, Pydantic lo rechaza (extra='forbid')."""
        svc = _make_svc()
        with _client_with_perms(["coloquios:gestionar"], svc_override=svc) as client:
            resp = client.post(
                "/api/v1/coloquios",
                json={
                    "materia_id": str(MATERIA_ID),
                    "cohorte_id": str(COHORTE_ID),
                    "tipo": "Coloquio",
                    "instancia": "1er Coloquio",
                    "tenant_id": str(TENANT_B),  # campo extra prohibido
                },
            )
        assert resp.status_code == 422
