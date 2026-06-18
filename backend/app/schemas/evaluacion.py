"""Schemas Pydantic v2 para el módulo de evaluaciones y coloquios (C-14).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.
tenant_id nunca se acepta en requests — viene siempre del JWT.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.evaluacion import EstadoReserva, TipoEvaluacion


# ── Evaluacion ────────────────────────────────────────────────────────────────


class EvaluacionCreate(BaseModel):
    """Payload para crear una convocatoria de coloquio/evaluación.

    cupos_por_dia: dict {fecha_iso: cupos_disponibles}
    Ejemplo: {"2026-07-10": 5, "2026-07-11": 3}
    tenant_id NO se acepta — viene del JWT.
    """

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: TipoEvaluacion
    instancia: str
    cupos_por_dia: dict[str, int] = {}


class EvaluacionRead(BaseModel):
    """Respuesta de una convocatoria de evaluación."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: TipoEvaluacion
    instancia: str
    cupos_por_dia: dict


class EvaluacionUpdate(BaseModel):
    """Payload para actualizar parcialmente una convocatoria.

    Todos los campos son opcionales — solo se actualizan los provistos.
    """

    model_config = ConfigDict(extra="forbid")

    instancia: Optional[str] = None
    cupos_por_dia: Optional[dict[str, int]] = None
    tipo: Optional[TipoEvaluacion] = None


# ── EvaluacionAlumno (importación masiva) ─────────────────────────────────────


class EvaluacionAlumnoImportRequest(BaseModel):
    """Payload para importar alumnos habilitados a una convocatoria."""

    model_config = ConfigDict(extra="forbid")

    alumno_ids: list[uuid.UUID]


class EvaluacionAlumnoImportResult(BaseModel):
    """Resultado de la importación de alumnos convocados."""

    model_config = ConfigDict(extra="forbid")

    total_convocados: int
    importados: int
    rechazados: list[uuid.UUID] = []


# ── ReservaEvaluacion ─────────────────────────────────────────────────────────


class ReservaEvaluacionCreate(BaseModel):
    """Payload para reservar un turno en una convocatoria.

    fecha: ISO date string YYYY-MM-DD del turno a reservar.
    evaluacion_id va en el path, no en el body.
    """

    model_config = ConfigDict(extra="forbid")

    fecha: str  # ISO date YYYY-MM-DD


class ReservaEvaluacionRead(BaseModel):
    """Respuesta de una reserva de turno."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    evaluacion_id: uuid.UUID
    alumno_id: uuid.UUID
    fecha: str
    estado: EstadoReserva


# ── ResultadoEvaluacion ───────────────────────────────────────────────────────


class ResultadoEvaluacionUpsert(BaseModel):
    """Payload para registrar o actualizar la nota final de un alumno.

    nota_final acepta texto ("Aprobado", "8.5", "Desaprobado", etc.).
    """

    model_config = ConfigDict(extra="forbid")

    alumno_id: uuid.UUID
    nota_final: str


class ResultadoEvaluacionRead(BaseModel):
    """Respuesta de un resultado de evaluación."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    evaluacion_id: uuid.UUID
    alumno_id: uuid.UUID
    nota_final: str


# ── Métricas ──────────────────────────────────────────────────────────────────


class MetricasColoquioRead(BaseModel):
    """Panel de métricas del módulo de coloquios para el tenant."""

    model_config = ConfigDict(extra="forbid")

    total_convocados: int
    instancias_activas: int
    reservas_activas: int
    notas_registradas: int


# ── Agenda ────────────────────────────────────────────────────────────────────


class AgendaEntradaRead(BaseModel):
    """Entrada de agenda: una reserva activa con datos del alumno."""

    model_config = ConfigDict(extra="forbid")

    reserva_id: uuid.UUID
    alumno_id: uuid.UUID
    fecha: str
    estado: EstadoReserva
