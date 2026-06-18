"""Schemas Pydantic v2 para el módulo de análisis de atrasados (C-11).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.
Son schemas de respuesta (output) — no se usan para input de DB.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AtrasadoItem(BaseModel):
    """Un alumno identificado como atrasado en una o más actividades."""

    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: str
    apellidos: str
    email: str  # descifrado en el service
    comision: Optional[str] = None
    actividades_faltantes: list[str]
    actividades_bajo_umbral: list[str]


class AtrasadoResponse(BaseModel):
    """Respuesta del endpoint GET /atrasados."""

    model_config = ConfigDict(extra="forbid")

    total_atrasados: int
    items: list[AtrasadoItem]


class RankingItem(BaseModel):
    """Un alumno en el ranking de actividades aprobadas."""

    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: str
    apellidos: str
    actividades_aprobadas: int
    posicion: int


class RankingResponse(BaseModel):
    """Respuesta del endpoint GET /ranking."""

    model_config = ConfigDict(extra="forbid")

    total: int
    items: list[RankingItem]


class ActividadMetrica(BaseModel):
    """Métricas de una actividad: nombre + porcentaje de aprobación."""

    model_config = ConfigDict(extra="forbid")

    actividad: str
    total_calificados: int
    total_aprobados: int
    pct_aprobacion: float


class ReporteRapidoResponse(BaseModel):
    """Respuesta del endpoint GET /reporte."""

    model_config = ConfigDict(extra="forbid")

    total_alumnos: int
    total_atrasados: int
    actividades_count: int
    metricas_por_actividad: list[ActividadMetrica]


class NotaFinalItem(BaseModel):
    """Nota final calculada para un alumno."""

    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: str
    apellidos: str
    nota_final: float
    actividades_incluidas: int


class NotaFinalResponse(BaseModel):
    """Respuesta del endpoint GET /notas-finales."""

    model_config = ConfigDict(extra="forbid")

    actividades_seleccionadas: list[str]
    items: list[NotaFinalItem]


class TpPendienteItem(BaseModel):
    """Un TP finalizado por el alumno pero sin corrección registrada."""

    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    apellidos: str
    nombre: str
    email: str  # descifrado
    actividad: str
    estado_finalizacion: str


class MonitorFiltros(BaseModel):
    """Filtros opcionales para el endpoint de monitor."""

    model_config = ConfigDict(extra="forbid")

    comision: Optional[str] = None
    busqueda_libre: Optional[str] = None
    estado_actividad: Optional[str] = None
    # scope seguimiento (TUTOR/PROFESOR)
    alumno: Optional[str] = None
    actividad: Optional[str] = None
    min_actividades_cumplidas: Optional[int] = None
    # scope coordinación (fechas)
    fecha_desde: Optional[str] = None  # ISO date string
    fecha_hasta: Optional[str] = None  # ISO date string


class MonitorItem(BaseModel):
    """Un alumno en el monitor con resumen de su estado académico."""

    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: str
    apellidos: str
    comision: Optional[str] = None
    actividades_aprobadas: int
    actividades_pendientes: int
    es_atrasado: bool


class MonitorResponse(BaseModel):
    """Respuesta del endpoint GET /monitor."""

    model_config = ConfigDict(extra="forbid")

    total: int
    items: list[MonitorItem]
