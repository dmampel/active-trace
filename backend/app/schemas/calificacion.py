"""Schemas Pydantic para el módulo de calificaciones (C-10).

Todos los schemas tienen extra='forbid' para rechazar campos no declarados.
La identidad (tenant_id, usuario_id) NUNCA se acepta como campo del body —
siempre proviene del JWT verificado.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Actividad detectada ───────────────────────────────────────────────────────


class ActividadDetectadaOut(BaseModel):
    """Actividad detectada por el parser en el archivo del LMS."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    escala: str  # "numerica" | "textual"
    columna_csv: str


# ── Preview ───────────────────────────────────────────────────────────────────


class PreviewCalificacionesOut(BaseModel):
    """Resultado del endpoint de preview — sin persistir datos."""

    model_config = ConfigDict(extra="forbid")

    actividades: list[ActividadDetectadaOut]
    total_alumnos: int


# ── Importación ───────────────────────────────────────────────────────────────


class ImportarCalificacionesRequest(BaseModel):
    """Body para importar calificaciones con actividades seleccionadas.

    El materia_id se toma de la URL, no del body.
    El tenant_id se toma del JWT, no del body.
    """

    model_config = ConfigDict(extra="forbid")

    actividades: list[ActividadDetectadaOut]
    seleccionadas: list[str]  # nombres de actividades a persistir
    filas: list[dict]         # filas crudas del preview, con entrada_padron_id


class ImportarCalificacionesOut(BaseModel):
    """Resultado de una importación de calificaciones."""

    model_config = ConfigDict(extra="forbid")

    filas_afectadas: int


# ── Calificación individual ───────────────────────────────────────────────────


class CalificacionOut(BaseModel):
    """Una calificación con su estado aprobado derivado (NO persistido)."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    entrada_padron_id: uuid.UUID
    materia_id: uuid.UUID
    actividad: str
    nota_numerica: Optional[float] = None
    nota_textual: Optional[str] = None
    origen: str
    importado_at: Optional[datetime] = None
    aprobado: Optional[bool] = None  # derivado en el momento de leer, no persistido


# ── Reporte de finalización ───────────────────────────────────────────────────


class FinalizacionEntradaRequest(BaseModel):
    """Una entrada del reporte de finalización del LMS."""

    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    actividad: str
    escala: str  # "textual" | "numerica"
    finalizado: bool


class FinalizacionReporteRequest(BaseModel):
    """Body para cruzar el reporte de finalización del LMS."""

    model_config = ConfigDict(extra="forbid")

    finalizaciones: list[FinalizacionEntradaRequest]


class SinCorregirOut(BaseModel):
    """Entrega textual finalizada sin calificación."""

    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    actividad: str


class FinalizacionReporteOut(BaseModel):
    """Resultado del cruce con el reporte de finalización."""

    model_config = ConfigDict(extra="forbid")

    sin_corregir: list[SinCorregirOut]
    total: int


# ── Configuración de umbral ───────────────────────────────────────────────────


class ConfigUmbralRequest(BaseModel):
    """Body para configurar el umbral de aprobación de una asignación docente.

    El tenant_id y asignacion_id se toman del JWT, no del body.
    """

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    umbral_pct: int
    valores_aprobatorios: list[str]


class ConfigUmbralOut(BaseModel):
    """Resultado de configurar el umbral."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    umbral_pct: int
    valores_aprobatorios: list[str]
