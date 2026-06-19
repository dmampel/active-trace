"""Schemas Pydantic v2 para el módulo de tareas internas (C-16).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.
tenant_id nunca se acepta en requests — viene siempre del JWT.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.tarea import EstadoTarea


# ── TareaCreate ───────────────────────────────────────────────────────────────


class TareaCreate(BaseModel):
    """Payload para crear una tarea interna.

    asignado_por y tenant_id NO se aceptan — vienen del JWT.
    El estado inicial siempre es pendiente (lo fija el servicio).
    """

    model_config = ConfigDict(extra="forbid")

    asignado_a: uuid.UUID
    descripcion: str
    materia_id: Optional[uuid.UUID] = None
    contexto_id: Optional[uuid.UUID] = None


# ── TareaOut ──────────────────────────────────────────────────────────────────


class TareaOut(BaseModel):
    """Respuesta con todos los campos públicos de una tarea."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    asignado_a: uuid.UUID
    asignado_por: uuid.UUID
    materia_id: Optional[uuid.UUID]
    estado: EstadoTarea
    descripcion: str
    contexto_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


# ── TareaEstadoUpdate ─────────────────────────────────────────────────────────


class TareaEstadoUpdate(BaseModel):
    """Payload para cambiar el estado de una tarea."""

    model_config = ConfigDict(extra="forbid")

    estado: EstadoTarea


# ── ComentarioCreate ──────────────────────────────────────────────────────────


class ComentarioCreate(BaseModel):
    """Payload para agregar un comentario a una tarea."""

    model_config = ConfigDict(extra="forbid")

    texto: str


# ── ComentarioOut ─────────────────────────────────────────────────────────────


class ComentarioOut(BaseModel):
    """Respuesta de un comentario de tarea."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    autor_id: uuid.UUID
    texto: str
    creado_at: datetime


# ── PaginatedTareas ───────────────────────────────────────────────────────────


class PaginatedTareas(BaseModel):
    """Respuesta paginada para la vista de admin de tareas."""

    model_config = ConfigDict(extra="forbid")

    total: int
    page: int
    size: int
    items: list[TareaOut]
