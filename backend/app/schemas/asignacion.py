"""Schemas Pydantic v2 para asignaciones contextuales.

Reglas:
- extra='forbid' en todos los schemas.
- AsignacionCreate: campos para crear una asignación.
- AsignacionUpdate: campos actualizables (todos opcionales).
- AsignacionRead: incluye estado_vigencia derivado (nunca almacenado).
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AsignacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario_id: uuid.UUID
    rol: str
    desde: date
    hasta: Optional[date] = None
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    comisiones: List[str] = []
    responsable_id: Optional[uuid.UUID] = None


class AsignacionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol: Optional[str] = None
    desde: Optional[date] = None
    hasta: Optional[date] = None
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    comisiones: Optional[List[str]] = None
    responsable_id: Optional[uuid.UUID] = None


class AsignacionRead(BaseModel):
    """DTO de respuesta: incluye estado_vigencia derivado en el service."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    rol: str
    desde: date
    hasta: Optional[date] = None
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    comisiones: List[str] = []
    responsable_id: Optional[uuid.UUID] = None
    estado_vigencia: str  # "Vigente" | "Vencida" | "Futura"
