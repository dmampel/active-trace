"""Schemas Pydantic v2 para el módulo de fechas académicas (C-14).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.
tenant_id nunca se acepta en requests — viene siempre del JWT.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.evaluacion import TipoFechaAcademica


class FechaAcademicaCreate(BaseModel):
    """Payload para crear una fecha académica.

    fecha: ISO date string YYYY-MM-DD.
    """

    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: TipoFechaAcademica
    numero: int
    periodo: str
    fecha: str  # ISO date YYYY-MM-DD
    titulo: str


class FechaAcademicaRead(BaseModel):
    """Respuesta de una fecha académica."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: TipoFechaAcademica
    numero: int
    periodo: str
    fecha: str
    titulo: str


class FechaAcademicaUpdate(BaseModel):
    """Payload para actualizar parcialmente una fecha académica.

    Todos los campos son opcionales — solo se actualizan los provistos.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: Optional[TipoFechaAcademica] = None
    numero: Optional[int] = None
    periodo: Optional[str] = None
    fecha: Optional[str] = None
    titulo: Optional[str] = None
