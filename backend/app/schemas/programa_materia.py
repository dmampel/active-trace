"""Schemas Pydantic v2 para el módulo de programas de materia (C-17).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.
tenant_id nunca se acepta en requests — viene siempre del JWT.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProgramaMateriaCreate(BaseModel):
    """Payload para crear un programa de materia.

    referencia_archivo es un texto opaco (URL, path, ID externo) — sin upload real.
    """

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    titulo: str
    referencia_archivo: Optional[str] = None


class ProgramaMateriaUpdate(BaseModel):
    """Payload para actualizar parcialmente un programa de materia.

    Solo titulo y referencia_archivo son actualizables.
    """

    model_config = ConfigDict(extra="forbid")

    titulo: Optional[str] = None
    referencia_archivo: Optional[str] = None


class ProgramaMateriaOut(BaseModel):
    """Respuesta de un programa de materia."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    titulo: str
    referencia_archivo: Optional[str]
    cargado_at: Optional[datetime]
