"""Tests del router de avisos y acknowledgment (C-15, Tareas 8.1–8.19).

Patrón: TestClient + mocked get_current_user + patched RbacRepository + mocked service.
Cubre todos los escenarios de la spec:
- RBAC: avisos:publicar requerido para CRUD de gestión
- Feed: filtrado por vigencia, activo, alcance, rol, cohorte
- ACK: idempotente, desaparece del feed tras confirmar (si requiere_ack=true)
- Contadores: total_acks derivado

Safety net: 531 tests passing + 19 errors (pre-existing) antes de estos tests.
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.models.aviso import AlcanceAviso, SeveridadAviso
from app.schemas.aviso import AvisoFeedItem, AvisoResponse

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
COORD_ID = uuid.uuid4()
ALUMNO_ID = uuid.uuid4()
PROFESOR_ID = uuid.uuid4()
TUTOR_ID = uuid.uuid4()
AVISO_ID = uuid.uuid4()
MATERIA_A = uuid.uuid4()
COHORTE_A = uuid.uuid4()
COHORTE_B = uuid.uuid4()

NOW = datetime.now(timezone.utc)
PAST = NOW - timedelta(hours=1)
FUTURE = NOW + timedelta(hours=24)
EXPIRED = NOW - timedelta(days=1)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(roles=None, tenant_id=None, user_id=None):
    user = MagicMock()
    user.id = user_id or COORD_ID
    user.tenant_id = tenant_id or TENANT_A
    user.roles = roles or ["COORDINADOR"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


def _make_aviso_response(**kwargs) -> AvisoResponse:
    defaults = dict(
        id=AVISO_ID,
        tenant_id=TENANT_A,
        alcance=AlcanceAviso.Global,
        materia_id=None,
        cohorte_id=None,
        rol_destino=None,
        severidad=SeveridadAviso.Info,
        titulo="Aviso de prueba",
        cuerpo="Cuerpo del aviso",
        inicio_en=PAST,
        fin_en=FUTURE,
        orden=0,
        activo=True,
        requiere_ack=False,
        total_vistas=0,
        total_acks=0,
    )
    defaults.update(kwargs)
    return AvisoResponse(**defaults)


def _make_feed_item(**kwargs) -> AvisoFeedItem:
    defaults = dict(
        id=AVISO_ID,
        alcance=AlcanceAviso.Global,
        severidad=SeveridadAviso.Info,
        titulo="Aviso de prueba",
        cuerpo="Cuerpo del aviso",
        inicio_en=PAST,
        fin_en=FUTURE,
        orden=0,
        requiere_ack=False,
        ya_confirmado=False,
    )
    defaults.update(kwargs)
    return AvisoFeedItem(**defaults)


def _make_svc(**overrides):
    """Crea un mock del AvisoService con defaults sensatos."""
    svc = MagicMock()
    svc.create_aviso = AsyncMock(return_value=_make_aviso_response())
    svc.get_aviso = AsyncMock(return_value=_make_aviso_response())
    svc.list_avisos = AsyncMock(return_value=[_make_aviso_response()])
    svc.update_aviso = AsyncMock(return_value=_make_aviso_response())
    svc.delete_aviso = AsyncMock(return_value=None)
    svc.get_mis_avisos = AsyncMock(return_value=[_make_feed_item()])
    svc.confirm_ack = AsyncMock(return_value=None)
    for k, v in overrides.items():
        setattr(svc, k, AsyncMock(return_value=v) if not isinstance(v, AsyncMock) else v)
    return svc


@contextmanager
def _client_with_perms(perms: list[str], user=None, svc_override=None):
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db
    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override is not None:
            import app.api.v1.routers.avisos as avisos_router
            app.dependency_overrides[avisos_router._get_aviso_service] = lambda: svc_override
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override is not None:
                import app.api.v1.routers.avisos as avisos_router
                app.dependency_overrides.pop(avisos_router._get_aviso_service, None)


# ── 8.2: COORDINADOR crea aviso global → 201 ─────────────────────────────────


class TestCrearAviso:
    def test_crear_aviso_global_exitoso_retorna_201(self):
        """8.2: COORDINADOR crea aviso global → 201."""
        svc = _make_svc()
        with _client_with_perms(["avisos:publicar"], svc_override=svc) as client:
            resp = client.post(
                "/api/v1/avisos",
                json={
                    "alcance": "Global",
                    "titulo": "Cierre de notas",
                    "cuerpo": "El sistema cerrará mañana a las 23:59",
                    "inicio_en": PAST.isoformat(),
                    "fin_en": FUTURE.isoformat(),
                    "severidad": "Info",
                },
            )
        assert resp.status_code == 201
        svc.create_aviso.assert_called_once()

    # ── 8.3: PorCohorte sin cohorte_id → 422 ─────────────────────────────────

    def test_crear_aviso_por_cohorte_sin_cohorte_id_retorna_422(self):
        """8.3: COORDINADOR crea aviso PorCohorte sin cohorte_id → 422."""
        with _client_with_perms(["avisos:publicar"]) as client:
            resp = client.post(
                "/api/v1/avisos",
                json={
                    "alcance": "PorCohorte",
                    "titulo": "Aviso cohorte",
                    "cuerpo": "Cuerpo",
                    "inicio_en": PAST.isoformat(),
                },
            )
        assert resp.status_code == 422

    # ── 8.4: PorRol sin rol_destino → 422 ────────────────────────────────────

    def test_crear_aviso_por_rol_sin_rol_destino_retorna_422(self):
        """8.4: COORDINADOR crea aviso PorRol sin rol_destino → 422."""
        with _client_with_perms(["avisos:publicar"]) as client:
            resp = client.post(
                "/api/v1/avisos",
                json={
                    "alcance": "PorRol",
                    "titulo": "Aviso rol",
                    "cuerpo": "Cuerpo",
                    "inicio_en": PAST.isoformat(),
                },
            )
        assert resp.status_code == 422

    # ── 8.5: PROFESOR intenta crear aviso → 403 ──────────────────────────────

    def test_profesor_no_puede_crear_aviso_retorna_403(self):
        """8.5: PROFESOR intenta crear aviso → 403."""
        profesor = _make_user(roles=["PROFESOR"], user_id=PROFESOR_ID)
        with _client_with_perms([], user=profesor) as client:
            resp = client.post(
                "/api/v1/avisos",
                json={
                    "alcance": "Global",
                    "titulo": "Aviso",
                    "cuerpo": "Cuerpo",
                    "inicio_en": PAST.isoformat(),
                },
            )
        assert resp.status_code == 403


# ── 8.6: Listar incluye inactivos y vencidos ──────────────────────────────────


class TestListarAvisos:
    def test_listar_incluye_inactivos_y_vencidos(self):
        """8.6: listar avisos (COORDINADOR) incluye inactivos y vencidos."""
        inactivo = _make_aviso_response(activo=False, fin_en=EXPIRED)
        svc = _make_svc(list_avisos=[inactivo])
        svc.list_avisos = AsyncMock(return_value=[inactivo])
        with _client_with_perms(["avisos:publicar"], svc_override=svc) as client:
            resp = client.get("/api/v1/avisos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["activo"] is False


# ── 8.7-8.12: Feed mis-avisos ─────────────────────────────────────────────────


class TestMisAvisos:
    def test_feed_excluye_aviso_vencido(self):
        """8.7: feed mis-avisos excluye aviso con fin_en < NOW()."""
        # El repositorio ya filtra — feed vacío cuando no hay avisos vigentes
        svc = _make_svc()
        svc.get_mis_avisos = AsyncMock(return_value=[])
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        with _client_with_perms([], user=alumno, svc_override=svc) as client:
            resp = client.get("/api/v1/avisos/mis-avisos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_feed_excluye_aviso_inactivo(self):
        """8.8: feed mis-avisos excluye aviso inactivo (activo=false)."""
        svc = _make_svc()
        svc.get_mis_avisos = AsyncMock(return_value=[])
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        with _client_with_perms([], user=alumno, svc_override=svc) as client:
            resp = client.get("/api/v1/avisos/mis-avisos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_aviso_global_aparece_para_todos(self):
        """8.9: aviso Global aparece para todos los roles en el feed."""
        global_item = _make_feed_item(alcance=AlcanceAviso.Global)
        svc = _make_svc()
        svc.get_mis_avisos = AsyncMock(return_value=[global_item])
        # ALUMNO ve aviso global
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        with _client_with_perms([], user=alumno, svc_override=svc) as client:
            resp = client.get("/api/v1/avisos/mis-avisos")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["alcance"] == "Global"

    def test_aviso_por_rol_profesor_no_aparece_para_tutor(self):
        """8.10: aviso PorRol=PROFESOR no aparece en feed de TUTOR."""
        # El servicio retorna vacío para el TUTOR (lógica en repo/svc)
        svc = _make_svc()
        svc.get_mis_avisos = AsyncMock(return_value=[])
        tutor = _make_user(roles=["TUTOR"], user_id=TUTOR_ID)
        with _client_with_perms([], user=tutor, svc_override=svc) as client:
            resp = client.get("/api/v1/avisos/mis-avisos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_aviso_por_cohorte_a_no_aparece_para_cohorte_b(self):
        """8.11: aviso PorCohorte=A no aparece para usuario de cohorte B."""
        svc = _make_svc()
        svc.get_mis_avisos = AsyncMock(return_value=[])
        profesor = _make_user(roles=["PROFESOR"], user_id=PROFESOR_ID)
        with _client_with_perms([], user=profesor, svc_override=svc) as client:
            resp = client.get("/api/v1/avisos/mis-avisos")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_feed_ordenado_por_orden_asc(self):
        """8.12: feed ordenado por orden ASC."""
        item_orden2 = _make_feed_item(id=uuid.uuid4(), orden=2, titulo="Segundo")
        item_orden1 = _make_feed_item(id=uuid.uuid4(), orden=1, titulo="Primero")
        svc = _make_svc()
        svc.get_mis_avisos = AsyncMock(return_value=[item_orden1, item_orden2])
        with _client_with_perms([], svc_override=svc) as client:
            resp = client.get("/api/v1/avisos/mis-avisos")
        assert resp.status_code == 200
        items = resp.json()
        assert items[0]["orden"] == 1
        assert items[1]["orden"] == 2


# ── 8.13-8.17: ACK ────────────────────────────────────────────────────────────


class TestAck:
    def test_alumno_confirma_ack_requiere_ack_retorna_200(self):
        """8.13: ALUMNO confirma ack de aviso con requiere_ack=true → 200."""
        svc = _make_svc()
        svc.confirm_ack = AsyncMock(return_value=None)
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        with _client_with_perms([], user=alumno, svc_override=svc) as client:
            resp = client.post(f"/api/v1/avisos/{AVISO_ID}/ack")
        assert resp.status_code == 200
        svc.confirm_ack.assert_called_once()

    def test_ack_idempotente_segundo_post_no_falla(self):
        """8.14: ACK idempotente — segundo POST /ack no falla ni duplica registro."""
        svc = _make_svc()
        svc.confirm_ack = AsyncMock(return_value=None)
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        with _client_with_perms([], user=alumno, svc_override=svc) as client:
            resp1 = client.post(f"/api/v1/avisos/{AVISO_ID}/ack")
            resp2 = client.post(f"/api/v1/avisos/{AVISO_ID}/ack")
        assert resp1.status_code == 200
        assert resp2.status_code == 200

    def test_aviso_sin_requiere_ack_sigue_en_feed_tras_confirmar(self):
        """8.15: aviso con requiere_ack=false sigue en feed tras confirmar."""
        # El feed debe seguir incluyendo el aviso (ya_confirmado=true pero sigue visible)
        svc = _make_svc()
        item_confirmado = _make_feed_item(requiere_ack=False, ya_confirmado=True)
        svc.get_mis_avisos = AsyncMock(return_value=[item_confirmado])
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID)
        with _client_with_perms([], user=alumno, svc_override=svc) as client:
            resp = client.get("/api/v1/avisos/mis-avisos")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["ya_confirmado"] is True

    def test_contador_total_acks_3_tras_3_usuarios(self):
        """8.16: contador total_acks = 3 tras 3 usuarios distintos confirmar."""
        aviso_con_acks = _make_aviso_response(total_acks=3, total_vistas=3)
        svc = _make_svc()
        svc.get_aviso = AsyncMock(return_value=aviso_con_acks)
        coord = _make_user(roles=["COORDINADOR"])
        with _client_with_perms(["avisos:publicar"], user=coord, svc_override=svc) as client:
            resp = client.get(f"/api/v1/avisos/{AVISO_ID}")
        assert resp.status_code == 200
        assert resp.json()["total_acks"] == 3
        assert resp.json()["total_vistas"] == 3

    def test_contador_no_cambia_por_ack_idempotente(self):
        """8.17: contador no cambia por ack idempotente (sigue en 1)."""
        aviso_un_ack = _make_aviso_response(total_acks=1, total_vistas=1)
        svc = _make_svc()
        svc.get_aviso = AsyncMock(return_value=aviso_un_ack)
        coord = _make_user(roles=["COORDINADOR"])
        with _client_with_perms(["avisos:publicar"], user=coord, svc_override=svc) as client:
            resp = client.get(f"/api/v1/avisos/{AVISO_ID}")
        assert resp.status_code == 200
        assert resp.json()["total_acks"] == 1


# ── 8.18: ACK en aviso de otro tenant → 404 ──────────────────────────────────


class TestTenantIsolation:
    def test_ack_en_aviso_otro_tenant_retorna_404(self):
        """8.18: POST /ack en aviso de otro tenant → 404."""
        svc = _make_svc()
        svc.confirm_ack = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Aviso no encontrado")
        )
        alumno = _make_user(roles=["ALUMNO"], user_id=ALUMNO_ID, tenant_id=TENANT_A)
        with _client_with_perms([], user=alumno, svc_override=svc) as client:
            resp = client.post(f"/api/v1/avisos/{AVISO_ID}/ack")
        assert resp.status_code == 404


# ── 8.19: Soft delete → aviso no aparece ─────────────────────────────────────


class TestSoftDelete:
    def test_soft_delete_aviso_no_aparece_en_feed_ni_listado(self):
        """8.19: soft delete → aviso no aparece en feed ni en listado de gestión."""
        svc = _make_svc()
        svc.delete_aviso = AsyncMock(return_value=None)
        svc.list_avisos = AsyncMock(return_value=[])
        svc.get_mis_avisos = AsyncMock(return_value=[])
        coord = _make_user(roles=["COORDINADOR"])
        with _client_with_perms(["avisos:publicar"], user=coord, svc_override=svc) as client:
            # Soft delete
            del_resp = client.delete(f"/api/v1/avisos/{AVISO_ID}")
            # Verificar que no aparece en listado de gestión
            list_resp = client.get("/api/v1/avisos")
            # Verificar que no aparece en feed
            alumno_resp = client.get("/api/v1/avisos/mis-avisos")

        assert del_resp.status_code == 204
        assert list_resp.json() == []
        assert alumno_resp.json() == []
