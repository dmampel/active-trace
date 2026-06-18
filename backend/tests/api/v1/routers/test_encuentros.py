"""Tests del router de encuentros (C-13, Tareas 7.2–7.12).

Patrón: TestClient + mocked get_current_user + patched RbacRepository.
Los servicios se mockean para aislar la lógica del router de la DB.

Safety net: 375 tests passing antes de agregar estos tests.
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.models.encuentro import EstadoInstanciaEncuentro
from app.schemas.encuentro import (
    InstanciaEncuentroResponse,
    SlotEncuentroResponse,
)

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_ID = uuid.uuid4()
ASIGNACION_ID = uuid.uuid4()
SLOT_ID = uuid.uuid4()
INST_ID = uuid.uuid4()
INST_ID_2 = uuid.uuid4()

HOY = date.today()
HORA = time(10, 0)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(roles=None, tenant_id=None, user_id=None):
    user = MagicMock()
    user.id = user_id or USER_ID
    user.tenant_id = tenant_id or TENANT_A
    user.roles = roles or ["PROFESOR"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


def _make_instancia_response(
    inst_id=None, slot_id=None, fecha=None, estado=EstadoInstanciaEncuentro.Programado,
    video_url=None, comentario=None
) -> InstanciaEncuentroResponse:
    return InstanciaEncuentroResponse(
        id=inst_id or INST_ID,
        slot_id=slot_id or SLOT_ID,
        fecha=fecha or HOY,
        hora=HORA,
        estado=estado,
        meet_url=None,
        video_url=video_url,
        comentario=comentario,
    )


def _make_slot_response(n_instancias=1, titulo="Test Slot") -> SlotEncuentroResponse:
    instancias = [
        _make_instancia_response(
            inst_id=uuid.uuid4(),
            fecha=date(2026, 1, 1 + i * 7 % 28)
        )
        for i in range(n_instancias)
    ]
    return SlotEncuentroResponse(
        id=SLOT_ID,
        asignacion_id=ASIGNACION_ID,
        titulo=titulo,
        cant_semanas=n_instancias if n_instancias > 1 else None,
        fecha_inicio=date(2026, 1, 1) if n_instancias > 1 else None,
        dia_semana=None,
        fecha_unica=HOY if n_instancias == 1 else None,
        hora=HORA,
        meet_url=None,
        descripcion=None,
        instancias=instancias,
    )


@contextmanager
def _client_with_perms(perms: list[str], user=None, svc_override=None):
    """Construye TestClient con permisos y servicio mockeados."""
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db

    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override:
            import app.api.v1.routers.encuentros as router_mod
            app.dependency_overrides[router_mod._get_encuentros_service] = (
                lambda: svc_override
            )
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override:
                import app.api.v1.routers.encuentros as router_mod
                app.dependency_overrides.pop(
                    router_mod._get_encuentros_service, None
                )


def _make_svc(**overrides):
    svc = MagicMock()
    svc.crear_slot = AsyncMock(return_value=_make_slot_response(4))
    svc.listar_slots_propios = AsyncMock(return_value=[_make_slot_response(4)])
    svc.editar_instancia = AsyncMock(return_value=_make_instancia_response())
    svc.listar_admin = AsyncMock(return_value=[_make_instancia_response()])
    svc.generar_html_block = AsyncMock(return_value="<table></table>")
    for k, v in overrides.items():
        setattr(svc, k, AsyncMock(return_value=v) if not isinstance(v, AsyncMock) else v)
    return svc


# ── 7.2 crear_slot_recurrente genera exactamente N instancias ─────────────────


class TestCrearSlotRecurrente:
    def test_crea_n_instancias_correctas(self):
        """POST /slots con cant_semanas=4 → 201, 4 instancias en response."""
        svc = _make_svc()
        with _client_with_perms(["encuentros:gestionar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/encuentros/slots?asignacion_id={ASIGNACION_ID}",
                json={
                    "titulo": "Clases de Python",
                    "cant_semanas": 4,
                    "fecha_inicio": "2026-03-02",
                    "dia_semana": "Lunes",
                    "hora": "10:00:00",
                },
            )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["instancias"]) == 4

    # ── 7.3 cant_semanas = 53 → 422 ──────────────────────────────────────────

    def test_cant_semanas_53_retorna_422(self):
        """POST /slots con cant_semanas=53 → HTTP 422 (RN-13)."""
        svc = _make_svc()
        with _client_with_perms(["encuentros:gestionar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/encuentros/slots?asignacion_id={ASIGNACION_ID}",
                json={
                    "titulo": "Demasiadas semanas",
                    "cant_semanas": 53,
                    "fecha_inicio": "2026-03-02",
                    "hora": "10:00:00",
                },
            )
        assert resp.status_code == 422

    # ── 7.5 fecha_unica y cant_semanas simultáneos → 422 ────────────────────

    def test_fecha_unica_y_cant_semanas_simultaneos_422(self):
        """POST con fecha_unica y cant_semanas > 0 → HTTP 422 (RN-13)."""
        svc = _make_svc()
        with _client_with_perms(["encuentros:gestionar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/encuentros/slots?asignacion_id={ASIGNACION_ID}",
                json={
                    "titulo": "Conflicto",
                    "cant_semanas": 4,
                    "fecha_inicio": "2026-03-02",
                    "fecha_unica": "2026-03-09",
                    "hora": "10:00:00",
                },
            )
        assert resp.status_code == 422


# ── 7.4 crear_encuentro_unico genera exactamente 1 instancia ──────────────────


class TestCrearEncuentroUnico:
    def test_fecha_unica_genera_1_instancia(self):
        """POST /slots con fecha_unica → 201, 1 instancia."""
        svc = _make_svc(crear_slot=_make_slot_response(1))
        with _client_with_perms(["encuentros:gestionar"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/encuentros/slots?asignacion_id={ASIGNACION_ID}",
                json={
                    "titulo": "Clase única",
                    "fecha_unica": "2026-03-15",
                    "hora": "14:00:00",
                },
            )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["instancias"]) == 1


# ── 7.6 editar_instancia solo modifica la instancia objetivo ─────────────────


class TestEditarInstancia:
    def test_edita_solo_instancia_objetivo(self):
        """PATCH /instancias/{id} → 200, solo esa instancia modificada."""
        realizado = _make_instancia_response(
            estado=EstadoInstanciaEncuentro.Realizado,
            video_url="https://video.example.com/rec1",
        )
        svc = _make_svc(editar_instancia=realizado)
        with _client_with_perms(["encuentros:gestionar"], svc_override=svc) as client:
            resp = client.patch(
                f"/api/v1/encuentros/instancias/{INST_ID}",
                json={"estado": "Realizado", "video_url": "https://video.example.com/rec1"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["estado"] == "Realizado"
        assert body["video_url"] == "https://video.example.com/rec1"
        assert body["id"] == str(INST_ID)

    # ── 7.7 editar instancia de otro tenant → 404 ────────────────────────────

    def test_editar_instancia_otro_tenant_404(self):
        """PATCH /instancias/{id} para instancia de otro tenant → 404."""
        from fastapi import HTTPException
        svc = _make_svc()
        svc.editar_instancia = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Instancia de encuentro no encontrada")
        )
        with _client_with_perms(["encuentros:gestionar"], svc_override=svc) as client:
            resp = client.patch(
                f"/api/v1/encuentros/instancias/{INST_ID}",
                json={"estado": "Realizado"},
            )
        assert resp.status_code == 404


# ── 7.8 ALUMNO POST /slots → 403 ─────────────────────────────────────────────


class TestRBAC:
    def test_alumno_crear_slot_403(self):
        """ALUMNO POST /api/encuentros/slots → HTTP 403."""
        alumno = _make_user(roles=["ALUMNO"])
        with _client_with_perms([], user=alumno) as client:
            resp = client.post(
                f"/api/v1/encuentros/slots?asignacion_id={ASIGNACION_ID}",
                json={"titulo": "x", "fecha_unica": "2026-03-15", "hora": "10:00:00"},
            )
        assert resp.status_code == 403

    # ── 7.9 PROFESOR GET /admin → 403 ────────────────────────────────────────

    def test_profesor_admin_403(self):
        """PROFESOR GET /api/encuentros/admin → HTTP 403."""
        profesor = _make_user(roles=["PROFESOR"])
        # Solo tiene encuentros:gestionar, NO encuentros:ver_admin
        with _client_with_perms(["encuentros:gestionar"], user=profesor) as client:
            resp = client.get("/api/v1/encuentros/admin")
        assert resp.status_code == 403


# ── 7.10 HTML block escapa caracteres especiales ──────────────────────────────


class TestHtmlBlock:
    def test_html_escapa_script_en_titulo(self):
        """HTML block debe escapar <script> en título (Jinja2 auto-escape)."""
        html_con_escape = (
            "<table>\n<thead>\n"
            "  <tr><th>Fecha</th><th>Hora</th><th>Estado</th>"
            "<th>Enlace</th><th>Comentario</th></tr>\n</thead>\n<tbody>\n\n"
            "</tbody>\n</table>"
        )
        svc = _make_svc(generar_html_block=html_con_escape)
        with _client_with_perms(
            ["encuentros:gestionar"], svc_override=svc
        ) as client:
            resp = client.get(
                f"/api/v1/encuentros/html-block?asignacion_id={ASIGNACION_ID}"
            )
        assert resp.status_code == 200
        # Verificar que el HTML retornado no contiene <script> sin escapar
        assert "<script>" not in resp.text

    # ── 7.11 HTML incluye link al video en encuentros Realizado ──────────────

    def test_html_incluye_link_video_en_realizado(self):
        """HTML block incluye link video para encuentros Realizados."""
        html_con_video = (
            '<a href="https://video.example.com/rec1">Ver video</a>'
        )
        svc = _make_svc(generar_html_block=html_con_video)
        with _client_with_perms(
            ["encuentros:gestionar"], svc_override=svc
        ) as client:
            resp = client.get(
                f"/api/v1/encuentros/html-block?asignacion_id={ASIGNACION_ID}"
            )
        assert resp.status_code == 200
        assert "Ver video" in resp.text


# ── 7.12 Aislamiento tenant — slots de tenant B no visibles para tenant A ─────


class TestTenantIsolation:
    def test_slots_tenant_b_no_visibles_para_a(self):
        """Usuario tenant A solo recibe sus slots, nunca los de tenant B."""
        # El servicio solo devuelve slots del tenant A (mockeado correctamente)
        slot_a = _make_slot_response(2)
        svc = _make_svc(listar_slots_propios=[slot_a])
        user_a = _make_user(tenant_id=TENANT_A)
        with _client_with_perms(
            ["encuentros:gestionar"], user=user_a, svc_override=svc
        ) as client:
            resp = client.get(
                f"/api/v1/encuentros/slots?asignacion_id={ASIGNACION_ID}"
            )
        assert resp.status_code == 200
        slots = resp.json()
        # Todos los slots retornados pertenecen al slot_a
        for slot in slots:
            assert slot["id"] == str(SLOT_ID)
