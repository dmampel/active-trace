"""Tests unitarios para schemas de análisis (C-11, Tarea 1.3).

Valida:
- Campos requeridos son obligatorios (ValueError si faltan)
- extra='forbid' rechaza campos extra
"""

import uuid
import pytest
from pydantic import ValidationError

from app.schemas.analisis import (
    AtrasadoItem,
    AtrasadoResponse,
    RankingItem,
    RankingResponse,
    ReporteRapidoResponse,
    ActividadMetrica,
    NotaFinalItem,
    NotaFinalResponse,
    TpPendienteItem,
    MonitorItem,
    MonitorResponse,
    MonitorFiltros,
)

_ID = uuid.uuid4()


# ── AtrasadoItem ──────────────────────────────────────────────────────────────


class TestAtrasadoItem:
    def test_campos_requeridos_validos(self):
        item = AtrasadoItem(
            entrada_padron_id=_ID,
            nombre="Juan",
            apellidos="Pérez",
            email="jp@test.com",
            actividades_faltantes=["TP1"],
            actividades_bajo_umbral=[],
        )
        assert item.nombre == "Juan"

    def test_rechaza_campo_extra(self):
        with pytest.raises(ValidationError):
            AtrasadoItem(
                entrada_padron_id=_ID,
                nombre="Juan",
                apellidos="Pérez",
                email="jp@test.com",
                actividades_faltantes=[],
                actividades_bajo_umbral=[],
                campo_extra="no-permitido",
            )

    def test_nombre_requerido(self):
        with pytest.raises(ValidationError):
            AtrasadoItem(
                entrada_padron_id=_ID,
                apellidos="Pérez",
                email="jp@test.com",
                actividades_faltantes=[],
                actividades_bajo_umbral=[],
            )


# ── RankingItem ───────────────────────────────────────────────────────────────


class TestRankingItem:
    def test_campos_requeridos_validos(self):
        item = RankingItem(
            entrada_padron_id=_ID,
            nombre="Ana",
            apellidos="García",
            actividades_aprobadas=3,
            posicion=1,
        )
        assert item.actividades_aprobadas == 3

    def test_rechaza_campo_extra(self):
        with pytest.raises(ValidationError):
            RankingItem(
                entrada_padron_id=_ID,
                nombre="Ana",
                apellidos="García",
                actividades_aprobadas=3,
                posicion=1,
                extra="no",
            )


# ── TpPendienteItem ───────────────────────────────────────────────────────────


class TestTpPendienteItem:
    def test_campos_requeridos_validos(self):
        item = TpPendienteItem(
            entrada_padron_id=_ID,
            apellidos="Rodríguez",
            nombre="Luis",
            email="lr@test.com",
            actividad="TP2",
            estado_finalizacion="Completado",
        )
        assert item.actividad == "TP2"

    def test_rechaza_campo_extra(self):
        with pytest.raises(ValidationError):
            TpPendienteItem(
                entrada_padron_id=_ID,
                apellidos="Rodríguez",
                nombre="Luis",
                email="lr@test.com",
                actividad="TP2",
                estado_finalizacion="Completado",
                no_existe="x",
            )


# ── MonitorItem ───────────────────────────────────────────────────────────────


class TestMonitorItem:
    def test_campos_requeridos_validos(self):
        item = MonitorItem(
            entrada_padron_id=_ID,
            nombre="María",
            apellidos="López",
            actividades_aprobadas=2,
            actividades_pendientes=1,
            es_atrasado=True,
        )
        assert item.es_atrasado is True

    def test_rechaza_campo_extra(self):
        with pytest.raises(ValidationError):
            MonitorItem(
                entrada_padron_id=_ID,
                nombre="María",
                apellidos="López",
                actividades_aprobadas=2,
                actividades_pendientes=1,
                es_atrasado=False,
                campo_invalido="x",
            )

    def test_comision_opcional(self):
        """comision es opcional — debe poder omitirse."""
        item = MonitorItem(
            entrada_padron_id=_ID,
            nombre="X",
            apellidos="Y",
            actividades_aprobadas=0,
            actividades_pendientes=0,
            es_atrasado=False,
        )
        assert item.comision is None


# ── MonitorFiltros ────────────────────────────────────────────────────────────


class TestMonitorFiltros:
    def test_todos_opcionales(self):
        """Sin parámetros → objeto vacío válido."""
        f = MonitorFiltros()
        assert f.comision is None
        assert f.min_actividades_cumplidas is None

    def test_rechaza_campo_extra(self):
        with pytest.raises(ValidationError):
            MonitorFiltros(campo_invalido="no")


# ── Response wrappers ─────────────────────────────────────────────────────────


class TestResponseWrappers:
    def test_atrasado_response_valido(self):
        r = AtrasadoResponse(total_atrasados=0, items=[])
        assert r.total_atrasados == 0

    def test_ranking_response_valido(self):
        r = RankingResponse(total=0, items=[])
        assert r.total == 0

    def test_nota_final_response_valido(self):
        r = NotaFinalResponse(actividades_seleccionadas=["TP1"], items=[])
        assert r.actividades_seleccionadas == ["TP1"]

    def test_monitor_response_valido(self):
        r = MonitorResponse(total=0, items=[])
        assert r.total == 0

    def test_reporte_rapido_response_valido(self):
        r = ReporteRapidoResponse(
            total_alumnos=10,
            total_atrasados=3,
            actividades_count=2,
            metricas_por_actividad=[],
        )
        assert r.total_alumnos == 10
