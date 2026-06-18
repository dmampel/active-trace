"""Lógica de dominio pura para análisis de alumnos atrasados (C-11).

ZERO I/O — sin SQLAlchemy, sin FastAPI, sin efectos secundarios.
Todas las funciones son determinísticas y testeables en total aislamiento.

DTOs internos (dataclasses simples) para comunicación entre capas:
- CalificacionDTO: nota de un alumno en una actividad
- AlumnoCalificacionesDTO: alumno + todas sus calificaciones
- FinalizacionDTO: estado de finalización de una actividad en el LMS
- UmbralDTO: configuración de umbral para una asignación

Reglas de negocio implementadas:
- RN-06: atrasado = al menos una actividad faltante o bajo umbral
- RN-07: solo actividades textuales entran en detección de TPs sin corregir
- RN-08: actividades numéricas se excluyen de TP sin corregir
- RN-09: ranking excluye alumnos sin ninguna actividad aprobada
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.domain.aprobado import derivar_aprobado

DEFAULT_UMBRAL_PCT: int = 60
DEFAULT_NOTA_MAXIMA: float = 10.0


# ── DTOs internos ─────────────────────────────────────────────────────────────


@dataclass
class CalificacionDTO:
    """Nota de un alumno en una actividad evaluable."""

    actividad: str
    nota_numerica: Optional[float]
    nota_textual: Optional[str]
    es_textual: bool  # True si la actividad es de escala textual (RN-08)


@dataclass
class AlumnoCalificacionesDTO:
    """Alumno del padrón con sus calificaciones para una materia."""

    entrada_padron_id: object  # uuid.UUID — tipado como object para evitar import circular
    nombre: str
    apellidos: str
    email: str  # descifrado
    comision: Optional[str]
    calificaciones: list[CalificacionDTO] = field(default_factory=list)


@dataclass
class FinalizacionDTO:
    """Estado de finalización de una actividad para un alumno, según el LMS."""

    entrada_padron_id: object  # uuid.UUID
    actividad: str
    estado: str  # e.g. "Completado", "En curso", "No iniciado"


@dataclass
class UmbralDTO:
    """Configuración de umbral de aprobación para una asignación."""

    umbral_pct: int
    valores_aprobatorios: list[str]
    nota_maxima: float = DEFAULT_NOTA_MAXIMA


# ── Funciones de dominio ──────────────────────────────────────────────────────


def es_atrasado(
    calificaciones: list[CalificacionDTO],
    actividades_seleccionadas: list[str],
    umbral_pct: int,
    valores_aprobatorios: list[str],
    nota_maxima: float = DEFAULT_NOTA_MAXIMA,
) -> tuple[bool, list[str], list[str]]:
    """Determina si un alumno está atrasado (RN-06).

    Un alumno está atrasado si para alguna actividad seleccionada:
    - No tiene calificación (faltante), O
    - Tiene nota pero no alcanza el umbral (bajo umbral).

    Args:
        calificaciones: calificaciones del alumno.
        actividades_seleccionadas: actividades a evaluar.
        umbral_pct: umbral de aprobación en porcentaje.
        valores_aprobatorios: valores textuales considerados aprobatorios.
        nota_maxima: escala máxima numérica.

    Returns:
        Tuple (es_atrasado, actividades_faltantes, actividades_bajo_umbral).
    """
    cal_por_actividad = {c.actividad: c for c in calificaciones}

    faltantes: list[str] = []
    bajo_umbral: list[str] = []

    for actividad in actividades_seleccionadas:
        cal = cal_por_actividad.get(actividad)
        if cal is None:
            faltantes.append(actividad)
        else:
            aprobado = derivar_aprobado(
                nota_numerica=cal.nota_numerica,
                nota_textual=cal.nota_textual,
                umbral_pct=umbral_pct,
                nota_maxima=nota_maxima,
                valores_aprobatorios=valores_aprobatorios,
            )
            if not aprobado:
                bajo_umbral.append(actividad)

    return bool(faltantes or bajo_umbral), faltantes, bajo_umbral


def calcular_ranking(
    alumnos: list[AlumnoCalificacionesDTO],
    umbral_pct: int,
    valores_aprobatorios: list[str],
    nota_maxima: float = DEFAULT_NOTA_MAXIMA,
) -> list[dict]:
    """Calcula el ranking de alumnos por actividades aprobadas (RN-09).

    Excluye alumnos sin ninguna actividad aprobada.
    Ordena descendentemente por cantidad de actividades aprobadas.

    Returns:
        Lista de dicts con campos: entrada_padron_id, nombre, apellidos,
        actividades_aprobadas, posicion.
    """
    resultado = []

    for alumno in alumnos:
        aprobadas = sum(
            1
            for c in alumno.calificaciones
            if derivar_aprobado(
                nota_numerica=c.nota_numerica,
                nota_textual=c.nota_textual,
                umbral_pct=umbral_pct,
                nota_maxima=nota_maxima,
                valores_aprobatorios=valores_aprobatorios,
            )
        )
        if aprobadas > 0:
            resultado.append(
                {
                    "entrada_padron_id": alumno.entrada_padron_id,
                    "nombre": alumno.nombre,
                    "apellidos": alumno.apellidos,
                    "actividades_aprobadas": aprobadas,
                }
            )

    # Ordenar descendente por aprobadas
    resultado.sort(key=lambda x: x["actividades_aprobadas"], reverse=True)

    # Asignar posición después del ordenamiento
    for i, item in enumerate(resultado, start=1):
        item["posicion"] = i

    return resultado


def calcular_notas_finales(
    alumnos: list[AlumnoCalificacionesDTO],
    actividades_seleccionadas: list[str],
) -> list[dict]:
    """Calcula la nota final para cada alumno sumando las actividades seleccionadas.

    Actividades faltantes valen 0. Solo se suman notas numéricas.

    Returns:
        Lista de dicts con: entrada_padron_id, nombre, apellidos,
        nota_final, actividades_incluidas.
    """
    resultado = []

    for alumno in alumnos:
        cal_por_actividad = {c.actividad: c for c in alumno.calificaciones}
        suma = 0.0
        incluidas = 0

        for actividad in actividades_seleccionadas:
            cal = cal_por_actividad.get(actividad)
            if cal is not None and cal.nota_numerica is not None:
                suma += float(cal.nota_numerica)
                incluidas += 1
            # Faltante o textual → 0 (ya lo da la suma inicial)

        resultado.append(
            {
                "entrada_padron_id": alumno.entrada_padron_id,
                "nombre": alumno.nombre,
                "apellidos": alumno.apellidos,
                "nota_final": round(suma, 4),
                "actividades_incluidas": incluidas,
            }
        )

    return resultado


def detectar_tp_sin_corregir(
    alumnos: list[AlumnoCalificacionesDTO],
    finalizaciones: list[FinalizacionDTO],
) -> list[dict]:
    """Detecta TPs finalizados por alumnos pero sin corrección textual registrada (RN-07, RN-08).

    Solo aplica a actividades de escala textual. Las numéricas se excluyen siempre.
    Un par (alumno, actividad) aparece como pendiente si:
    - El alumno tiene estado finalizado en el LMS para esa actividad textual, Y
    - No tiene calificación textual ni numérica registrada.

    Args:
        alumnos: alumnos con sus calificaciones (para lookup rápido).
        finalizaciones: reportes de finalización del LMS.

    Returns:
        Lista de dicts con: entrada_padron_id, apellidos, nombre, email,
        actividad, estado_finalizacion.
    """
    # Construir índice: entrada_padron_id → {actividad → calificacion}
    cal_index: dict = {}
    alumno_index: dict = {}
    for alumno in alumnos:
        cal_index[alumno.entrada_padron_id] = {
            c.actividad: c for c in alumno.calificaciones
        }
        alumno_index[alumno.entrada_padron_id] = alumno

    pendientes = []
    for fin in finalizaciones:
        cals = cal_index.get(fin.entrada_padron_id, {})
        cal = cals.get(fin.actividad)

        # RN-08: excluir si la calificación existente es numérica (no textual)
        if cal is not None and not cal.es_textual:
            continue

        # RN-07: solo actividades textuales (chequear en la finalizacion o en cal)
        # Si hay calificacion, es textual y ya tiene nota → no pendiente
        if cal is not None and (cal.nota_textual is not None or cal.nota_numerica is not None):
            continue

        # Sin calificación → pendiente
        alumno = alumno_index.get(fin.entrada_padron_id)
        if alumno is None:
            continue

        pendientes.append(
            {
                "entrada_padron_id": fin.entrada_padron_id,
                "apellidos": alumno.apellidos,
                "nombre": alumno.nombre,
                "email": alumno.email,
                "actividad": fin.actividad,
                "estado_finalizacion": fin.estado,
            }
        )

    return pendientes
