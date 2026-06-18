"""Tests TDD para funciones de dominio puro de análisis de atrasados (C-11, Tarea 2.5).

ZERO dependencias de DB. Datos sintéticos.
Cada función tiene al menos 2 casos: happy path + edge case.

Funciones testeadas:
- es_atrasado (RN-06)
- calcular_ranking (RN-09)
- calcular_notas_finales
- detectar_tp_sin_corregir (RN-07, RN-08)
"""

import uuid
import pytest

from app.domain.atrasados import (
    AlumnoCalificacionesDTO,
    CalificacionDTO,
    FinalizacionDTO,
    calcular_notas_finales,
    calcular_ranking,
    detectar_tp_sin_corregir,
    es_atrasado,
)

APROBATORIOS = ["Satisfactorio", "Supera lo esperado"]
UMBRAL = 60
NOTA_MAX = 10.0

_ID1 = uuid.uuid4()
_ID2 = uuid.uuid4()


# ── es_atrasado ───────────────────────────────────────────────────────────────


class TestEsAtrasado:
    def test_alumno_con_nota_menor_al_umbral_es_atrasado(self):
        """RN-06: nota numérica < umbral → atrasado."""
        cals = [CalificacionDTO("TP1", nota_numerica=4.0, nota_textual=None, es_textual=False)]
        atrasado, faltantes, bajo = es_atrasado(cals, ["TP1"], UMBRAL, APROBATORIOS)
        assert atrasado is True
        assert "TP1" in bajo
        assert faltantes == []

    def test_alumno_con_actividad_faltante_es_atrasado(self):
        """RN-06: sin calificación para actividad seleccionada → atrasado."""
        cals = []
        atrasado, faltantes, bajo = es_atrasado(cals, ["TP1"], UMBRAL, APROBATORIOS)
        assert atrasado is True
        assert "TP1" in faltantes

    def test_alumno_con_nota_textual_aprobatoria_no_es_atrasado(self):
        """Nota textual en conjunto aprobatorio → no atrasado."""
        cals = [CalificacionDTO("TP1", nota_numerica=None, nota_textual="Satisfactorio", es_textual=True)]
        atrasado, faltantes, bajo = es_atrasado(cals, ["TP1"], UMBRAL, APROBATORIOS, NOTA_MAX)
        assert atrasado is False
        assert faltantes == []
        assert bajo == []

    def test_alumno_aprueba_todas_no_es_atrasado(self):
        """Triangulación: múltiples actividades todas aprobadas → no atrasado."""
        cals = [
            CalificacionDTO("TP1", nota_numerica=7.0, nota_textual=None, es_textual=False),
            CalificacionDTO("TP2", nota_numerica=8.0, nota_textual=None, es_textual=False),
        ]
        atrasado, faltantes, bajo = es_atrasado(cals, ["TP1", "TP2"], UMBRAL, APROBATORIOS)
        assert atrasado is False

    def test_actividad_no_seleccionada_no_cuenta(self):
        """Triangulación: actividad fuera de selección no afecta el resultado."""
        cals = [CalificacionDTO("TP_OTRO", nota_numerica=2.0, nota_textual=None, es_textual=False)]
        atrasado, faltantes, bajo = es_atrasado(cals, ["TP1"], UMBRAL, APROBATORIOS)
        # TP1 es faltante (no TP_OTRO)
        assert atrasado is True
        assert "TP1" in faltantes

    def test_nota_exactamente_en_umbral_aprueba(self):
        """Límite inclusivo: nota == umbral_pct → aprobado."""
        cals = [CalificacionDTO("TP1", nota_numerica=6.0, nota_textual=None, es_textual=False)]
        atrasado, _, _ = es_atrasado(cals, ["TP1"], 60, [], 10.0)
        assert atrasado is False


# ── calcular_ranking ──────────────────────────────────────────────────────────


class TestCalcularRanking:
    def _alumno(self, aid, nombre, cals):
        return AlumnoCalificacionesDTO(
            entrada_padron_id=aid,
            nombre=nombre,
            apellidos="Apellido",
            email="test@t.com",
            comision=None,
            calificaciones=cals,
        )

    def test_alumno_con_aprobadas_aparece_en_ranking(self):
        """RN-09: alumno con al menos una aprobada → aparece."""
        alumno = self._alumno(
            _ID1, "Juan",
            [CalificacionDTO("TP1", nota_numerica=8.0, nota_textual=None, es_textual=False)],
        )
        result = calcular_ranking([alumno], UMBRAL, APROBATORIOS)
        assert len(result) == 1
        assert result[0]["actividades_aprobadas"] == 1

    def test_alumno_sin_aprobadas_no_aparece(self):
        """RN-09: sin aprobadas → excluido del ranking."""
        alumno = self._alumno(
            _ID1, "Ana",
            [CalificacionDTO("TP1", nota_numerica=3.0, nota_textual=None, es_textual=False)],
        )
        result = calcular_ranking([alumno], UMBRAL, APROBATORIOS)
        assert len(result) == 0

    def test_ranking_ordenado_descendente(self):
        """Triangulación: orden descendente por aprobadas."""
        alumno1 = self._alumno(
            _ID1, "Ana",
            [
                CalificacionDTO("TP1", nota_numerica=8.0, nota_textual=None, es_textual=False),
                CalificacionDTO("TP2", nota_numerica=9.0, nota_textual=None, es_textual=False),
            ],
        )
        alumno2 = self._alumno(
            _ID2, "Luis",
            [CalificacionDTO("TP1", nota_numerica=7.0, nota_textual=None, es_textual=False)],
        )
        result = calcular_ranking([alumno1, alumno2], UMBRAL, APROBATORIOS)
        assert result[0]["actividades_aprobadas"] == 2  # Ana primero
        assert result[0]["posicion"] == 1
        assert result[1]["posicion"] == 2

    def test_lista_vacia_retorna_vacia(self):
        """Edge: sin alumnos → lista vacía."""
        assert calcular_ranking([], UMBRAL, APROBATORIOS) == []

    def test_alumno_sin_calificaciones_excluido(self):
        """Edge: alumno sin ninguna calificación → no aparece."""
        alumno = self._alumno(_ID1, "X", [])
        result = calcular_ranking([alumno], UMBRAL, APROBATORIOS)
        assert len(result) == 0


# ── calcular_notas_finales ────────────────────────────────────────────────────


class TestCalcularNotasFinales:
    def _alumno(self, aid, nombre, cals):
        return AlumnoCalificacionesDTO(
            entrada_padron_id=aid,
            nombre=nombre,
            apellidos="Ap",
            email="e@t.com",
            comision=None,
            calificaciones=cals,
        )

    def test_nota_final_suma_actividades_seleccionadas(self):
        """Suma de actividades seleccionadas."""
        alumno = self._alumno(
            _ID1, "X",
            [
                CalificacionDTO("TP1", nota_numerica=7.0, nota_textual=None, es_textual=False),
                CalificacionDTO("TP2", nota_numerica=8.0, nota_textual=None, es_textual=False),
                CalificacionDTO("TP3", nota_numerica=5.0, nota_textual=None, es_textual=False),
            ],
        )
        result = calcular_notas_finales([alumno], ["TP1", "TP2"])
        assert result[0]["nota_final"] == 15.0
        assert result[0]["actividades_incluidas"] == 2

    def test_actividad_faltante_vale_cero(self):
        """Actividad no calificada suma 0."""
        alumno = self._alumno(
            _ID1, "Y",
            [CalificacionDTO("TP1", nota_numerica=7.0, nota_textual=None, es_textual=False)],
        )
        result = calcular_notas_finales([alumno], ["TP1", "TP2"])
        assert result[0]["nota_final"] == 7.0
        assert result[0]["actividades_incluidas"] == 1

    def test_alumno_sin_calificaciones_nota_cero(self):
        """Triangulación: sin ninguna calificación → nota_final = 0."""
        alumno = self._alumno(_ID1, "Z", [])
        result = calcular_notas_finales([alumno], ["TP1", "TP2"])
        assert result[0]["nota_final"] == 0.0
        assert result[0]["actividades_incluidas"] == 0

    def test_lista_vacia_de_actividades_nota_cero(self):
        """Edge: sin actividades seleccionadas → nota 0."""
        alumno = self._alumno(
            _ID1, "W",
            [CalificacionDTO("TP1", nota_numerica=9.0, nota_textual=None, es_textual=False)],
        )
        result = calcular_notas_finales([alumno], [])
        assert result[0]["nota_final"] == 0.0


# ── detectar_tp_sin_corregir ──────────────────────────────────────────────────


class TestDetectarTpSinCorregir:
    def _alumno(self, aid, cals=None):
        return AlumnoCalificacionesDTO(
            entrada_padron_id=aid,
            nombre="Juan",
            apellidos="Pérez",
            email="jp@t.com",
            comision=None,
            calificaciones=cals or [],
        )

    def test_textual_finalizada_sin_nota_es_pendiente(self):
        """RN-07: textual + finalizado + sin nota → pendiente."""
        alumno = self._alumno(_ID1)
        fins = [FinalizacionDTO(_ID1, "TP1", "Completado")]
        result = detectar_tp_sin_corregir([alumno], fins)
        assert len(result) == 1
        assert result[0]["actividad"] == "TP1"

    def test_textual_ya_calificada_no_es_pendiente(self):
        """Actividad textual con nota registrada → no pendiente."""
        alumno = self._alumno(
            _ID1,
            [CalificacionDTO("TP1", nota_numerica=None, nota_textual="Satisfactorio", es_textual=True)],
        )
        fins = [FinalizacionDTO(_ID1, "TP1", "Completado")]
        result = detectar_tp_sin_corregir([alumno], fins)
        assert len(result) == 0

    def test_actividad_numerica_no_aparece(self):
        """RN-08: actividad numérica → excluida del listado."""
        alumno = self._alumno(_ID1)
        # Calificación numérica existente → excluye
        alumno.calificaciones.append(
            CalificacionDTO("TP_NUM", nota_numerica=7.0, nota_textual=None, es_textual=False)
        )
        fins = [FinalizacionDTO(_ID1, "TP_NUM", "Completado")]
        result = detectar_tp_sin_corregir([alumno], fins)
        assert len(result) == 0

    def test_multiple_pendientes(self):
        """Triangulación: múltiples pendientes en distintos alumnos."""
        a1 = self._alumno(_ID1)
        a2 = AlumnoCalificacionesDTO(_ID2, "Ana", "García", "ag@t.com", None, [])
        fins = [
            FinalizacionDTO(_ID1, "TP1", "Completado"),
            FinalizacionDTO(_ID2, "TP2", "Completado"),
        ]
        result = detectar_tp_sin_corregir([a1, a2], fins)
        assert len(result) == 2

    def test_alumno_desconocido_ignorado(self):
        """Edge: finalizacion de alumno no en la lista → ignorado."""
        alumno = self._alumno(_ID1)
        fins = [FinalizacionDTO(uuid.uuid4(), "TP1", "Completado")]  # ID diferente
        result = detectar_tp_sin_corregir([alumno], fins)
        assert len(result) == 0
