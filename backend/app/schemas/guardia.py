"""Schemas Pydantic v2 para el módulo de guardias (C-13).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.

NOTA IMPORTANTE: `asignacion_id` NO está en GuardiaCreate — se toma del JWT
en el service. Incluirlo aquí sería una violación de la regla dura #8.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.guardia import EstadoGuardia


# ── GuardiaCreate ─────────────────────────────────────────────────────────────


class GuardiaCreate(BaseModel):
    """Payload para registrar una guardia.

    asignacion_id NO se incluye — se toma del JWT (regla dura #8).
    """

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    dia: date
    horario: str
    estado: EstadoGuardia = EstadoGuardia.Pendiente
    comentarios: Optional[str] = None

    @field_validator("horario")
    @classmethod
    def horario_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("horario no puede estar vacío")
        return v.strip()


# ── GuardiaFilter ─────────────────────────────────────────────────────────────


class GuardiaFilter(BaseModel):
    """Query params para filtrar guardias en listado y export.

    Todos los filtros son opcionales.
    """

    model_config = ConfigDict(extra="forbid")

    materia_id: Optional[uuid.UUID] = None
    estado: Optional[EstadoGuardia] = None
    desde: Optional[date] = None
    hasta: Optional[date] = None


# ── GuardiaResponse ───────────────────────────────────────────────────────────


class GuardiaResponse(BaseModel):
    """Respuesta de una guardia registrada."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    carrera_id: Optional[uuid.UUID]
    cohorte_id: Optional[uuid.UUID]
    dia: date
    horario: str
    estado: EstadoGuardia
    comentarios: Optional[str]
