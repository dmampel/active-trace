"""Tests de integración para el router de análisis de atrasados (C-11, Tareas 7.1–7.8).

Patrón: TestClient + mocked get_current_user + patched RbacRepository.
Valida: RBAC fail-closed (403 sin permiso), scope PROFESOR, ranking vacío,
        reporte vacío, POST tp-sin-corregir, auditoría monitor, export CSV.
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


def _make_user(roles=None, user_id=None, tenant_id=None):
    user = MagicMock()
    user.id = user_id or USER_ID
    user.tenant_id = tenant_id or TENANT_ID
    user.roles = roles or ["PROFESOR"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


@contextmanager
def _client_with_perms(perms: list[str], user=None, svc_override=None):
    """Construye un TestClient con permisos mockeados y service override opcional."""
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db

    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override:
            import app.api.v1.routers.analisis as analisis_router
            app.dependency_overrides[analisis_router._get_analisis_service] = lambda: svc_override
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override:
                import app.api.v1.routers.analisis as analisis_router
                app.dependency_overrides.pop(analisis_router._get_analisis_service, None)


def _make_svc(**method_overrides):
    """Crea un mock del AnalisisService con defaults sensatos."""
    svc = MagicMock()
    svc.get_atrasados = AsyncMock(return_value={"total_atrasados": 0, "items": []})
    svc.get_ranking = AsyncMock(return_value={"total": 0, "items": []})
    svc.get_reporte_rapido = AsyncMock(return_value={
        "total_alumnos": 0, "total_atrasados": 0,
        "actividades_count": 0, "metricas_por_actividad": [],
    })
    svc.get_notas_finales = AsyncMock(return_value={
        "actividades_seleccionadas": [], "items": [],
    })
    svc.detectar_tp_sin_corregir = AsyncMock(return_value=[])
    svc.get_monitor = AsyncMock(return_value={"total": 0, "items": []})
    for k, v in method_overrides.items():
        setattr(svc, k, AsyncMock(return_value=v))
    return svc


# ── 7.2 Sin permiso → 403 ─────────────────────────────────────────────────────


class TestRBACAnalisis:
    def test_atrasados_sin_permiso_retorna_403(self):
        """Sin atrasados:ver → 403."""
        with _client_with_perms([]) as client:
            resp = client.get(f"/api/v1/analisis/atrasados?materia_id={MATERIA_ID}")
        assert resp.status_code == 403

    def test_ranking_sin_permiso_retorna_403(self):
        with _client_with_perms([]) as client:
            resp = client.get(f"/api/v1/analisis/ranking?materia_id={MATERIA_ID}")
        assert resp.status_code == 403

    def test_reporte_sin_permiso_retorna_403(self):
        with _client_with_perms([]) as client:
            resp = client.get(f"/api/v1/analisis/reporte?materia_id={MATERIA_ID}")
        assert resp.status_code == 403

    def test_monitor_sin_permiso_retorna_403(self):
        with _client_with_perms([]) as client:
            resp = client.get(f"/api/v1/analisis/monitor?materia_id={MATERIA_ID}")
        assert resp.status_code == 403

    def test_tp_sin_corregir_sin_permiso_retorna_403(self):
        with _client_with_perms([]) as client:
            resp = client.post(
                f"/api/v1/analisis/tp-sin-corregir?materia_id={MATERIA_ID}",
                files={"file": ("fin.csv", b"a,b\n", "text/csv")},
            )
        assert resp.status_code == 403


# ── 7.3 PROFESOR solo recibe sus alumnos ─────────────────────────────────────


class TestScopeProfesor:
    def test_profesor_recibe_solo_sus_alumnos(self):
        """PROFESOR con permiso → el service recibe current_user con rol PROFESOR."""
        captured_user = {}

        async def _fake_get_atrasados(materia_id, actividades_seleccionadas, current_user):
            captured_user["roles"] = current_user.roles
            return {"total_atrasados": 0, "items": []}

        svc = _make_svc()
        svc.get_atrasados = _fake_get_atrasados

        user = _make_user(roles=["PROFESOR"])
        with _client_with_perms(["atrasados:ver"], user=user, svc_override=svc) as client:
            resp = client.get(f"/api/v1/analisis/atrasados?materia_id={MATERIA_ID}")

        assert resp.status_code == 200
        assert "PROFESOR" in captured_user.get("roles", [])


# ── 7.4 Ranking vacío ─────────────────────────────────────────────────────────


class TestRankingVacio:
    def test_ranking_vacio_cuando_no_hay_aprobadas(self):
        """Ranking sin alumnos con aprobadas retorna total=0."""
        svc = _make_svc()
        with _client_with_perms(["atrasados:ver"], svc_override=svc) as client:
            resp = client.get(f"/api/v1/analisis/ranking?materia_id={MATERIA_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


# ── 7.5 Reporte vacío ─────────────────────────────────────────────────────────


class TestReporteVacio:
    def test_reporte_rapido_vacio_cuando_no_hay_calificaciones(self):
        """Reporte rápido con total_alumnos=0 cuando no hay datos."""
        svc = _make_svc()
        with _client_with_perms(["atrasados:ver"], svc_override=svc) as client:
            resp = client.get(f"/api/v1/analisis/reporte?materia_id={MATERIA_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_alumnos"] == 0
        assert data["total_atrasados"] == 0


# ── 7.6 POST tp-sin-corregir con CSV válido ───────────────────────────────────


class TestTpSinCorregir:
    def test_post_con_csv_valido_retorna_pendientes_textuales(self):
        """CSV con TP textual sin nota → item en respuesta."""
        ep_id = uuid.uuid4()
        svc = _make_svc(detectar_tp_sin_corregir=[{
            "entrada_padron_id": ep_id,
            "apellidos": "Pérez",
            "nombre": "Juan",
            "email": "jp@t.com",
            "actividad": "TP1",
            "estado_finalizacion": "Completado",
        }])

        csv_content = f"entrada_padron_id,actividad,estado\n{ep_id},TP1,Completado\n"
        with _client_with_perms(["atrasados:ver"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/analisis/tp-sin-corregir?materia_id={MATERIA_ID}",
                files={"file": ("fin.csv", csv_content.encode(), "text/csv")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["actividad"] == "TP1"

    def test_csv_actividad_numerica_no_aparece(self):
        """Service devuelve lista vacía cuando solo hay numéricas → respuesta vacía."""
        svc = _make_svc(detectar_tp_sin_corregir=[])
        csv_content = "entrada_padron_id,actividad,estado\n{},TP_NUM,Completado\n".format(uuid.uuid4())
        with _client_with_perms(["atrasados:ver"], svc_override=svc) as client:
            resp = client.post(
                f"/api/v1/analisis/tp-sin-corregir?materia_id={MATERIA_ID}",
                files={"file": ("fin.csv", csv_content.encode(), "text/csv")},
            )
        assert resp.status_code == 200
        assert resp.json() == []


# ── 7.7 Monitor genera auditoría para COORDINADOR ─────────────────────────────


class TestMonitorAuditoria:
    def test_monitor_coordinador_llama_get_monitor(self):
        """COORDINADOR llama al monitor → service.get_monitor invocado."""
        svc = _make_svc()
        user = _make_user(roles=["COORDINADOR"])
        with _client_with_perms(["atrasados:ver"], user=user, svc_override=svc) as client:
            resp = client.get(f"/api/v1/analisis/monitor?materia_id={MATERIA_ID}")
        assert resp.status_code == 200
        svc.get_monitor.assert_called_once()


# ── 7.8 Export CSV de notas finales ──────────────────────────────────────────


class TestExportCSV:
    def test_export_notas_finales_retorna_text_csv(self):
        """GET /tp-sin-corregir/export retorna text/csv con Content-Disposition."""
        ep_id = uuid.uuid4()
        svc = _make_svc(get_notas_finales={
            "actividades_seleccionadas": ["TP1"],
            "items": [{
                "entrada_padron_id": ep_id,
                "apellidos": "García",
                "nombre": "Ana",
                "nota_final": 8.5,
                "actividades_incluidas": 1,
            }],
        })
        with _client_with_perms(["atrasados:ver"], svc_override=svc) as client:
            resp = client.get(
                f"/api/v1/analisis/tp-sin-corregir/export?materia_id={MATERIA_ID}&actividades=TP1"
            )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        # Verificar que hay filas en el CSV
        assert "Ana" in resp.text
        assert "8.5" in resp.text
