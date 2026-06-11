"""Schemas Pydantic v2 para operaciones de equipos docentes (C-08).

Reglas:
- extra='forbid' en todos los schemas.
- Ningún campo deriva estado de la DB — estado_vigencia se calcula en el Service.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Query params ──────────────────────────────────────────────────────────────

class MisAsignacionesQuery(BaseModel):
    """Query params para GET /equipos/mis-asignaciones."""
    model_config = ConfigDict(extra="forbid")

    estado_vigencia: Optional[str] = None
    materia_id: Optional[uuid.UUID] = None
    rol: Optional[str] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None


class BuscarUsuariosQuery(BaseModel):
    """Query params para GET /equipos/usuarios/buscar."""
    model_config = ConfigDict(extra="forbid")

    q: str = Field(..., min_length=2)
    limit: int = Field(default=20, le=50, ge=1)


# ── Response: mis-asignaciones ────────────────────────────────────────────────

class AsignacionDetalleResponse(BaseModel):
    """DTO de respuesta enriquecida para mis-asignaciones."""
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    rol: str
    materia: Optional[str] = None       # nombre de la materia
    carrera: Optional[str] = None       # nombre de la carrera
    cohorte: Optional[str] = None       # nombre / label de la cohorte
    desde: date
    hasta: Optional[date] = None
    estado_vigencia: str                # "Vigente" | "Vencida" | "Futura"
    responsable_id: Optional[uuid.UUID] = None


# ── Response: búsqueda de usuarios ───────────────────────────────────────────

class UsuarioBusquedaResponse(BaseModel):
    """DTO de respuesta para la búsqueda asistida de usuarios."""
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    legajo: Optional[str] = None


# ── Request/Response: asignación masiva ──────────────────────────────────────

class AsignacionMasivaRequest(BaseModel):
    """Body para POST /equipos/masiva."""
    model_config = ConfigDict(extra="forbid")

    usuario_ids: List[uuid.UUID] = Field(..., min_length=1)
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: uuid.UUID
    rol: str
    desde: date
    hasta: Optional[date] = None


class AsignacionMasivaResponse(BaseModel):
    """DTO de respuesta para asignación masiva."""
    model_config = ConfigDict(extra="forbid")

    creadas: int


# ── Request/Response: clonar equipo ──────────────────────────────────────────

class ContextoEquipo(BaseModel):
    """Sub-schema reutilizable para identificar un equipo (origen o destino)."""
    model_config = ConfigDict(extra="forbid")

    cohorte_id: uuid.UUID
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None


class ClonarEquipoRequest(BaseModel):
    """Body para POST /equipos/clonar."""
    model_config = ConfigDict(extra="forbid")

    origen: ContextoEquipo
    destino: ContextoEquipo


class ClonarEquipoResponse(BaseModel):
    """DTO de respuesta para clonación de equipo."""
    model_config = ConfigDict(extra="forbid")

    clonadas: int
    omitidas: int


# ── Request/Response: vigencia general ───────────────────────────────────────

class VigenciaEquipoRequest(BaseModel):
    """Body para PATCH /equipos/vigencia.

    Al menos uno de `desde` o `hasta` debe estar presente.
    """
    model_config = ConfigDict(extra="forbid")

    cohorte_id: uuid.UUID
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    desde: Optional[date] = None
    hasta: Optional[date] = None

    @model_validator(mode="after")
    def at_least_one_date(self) -> "VigenciaEquipoRequest":
        if self.desde is None and self.hasta is None:
            raise ValueError("Al menos uno de 'desde' o 'hasta' debe estar presente")
        return self


class VigenciaEquipoResponse(BaseModel):
    """DTO de respuesta para actualización masiva de vigencia."""
    model_config = ConfigDict(extra="forbid")

    actualizadas: int
