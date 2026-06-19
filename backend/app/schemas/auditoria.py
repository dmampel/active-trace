"""Schemas Pydantic v2 para el panel de auditoría y métricas (C-19).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.
Son schemas de respuesta (output) — no se usan para escritura en DB.
La identidad y el tenant se obtienen SIEMPRE del JWT; nunca de la petición.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditLogEntryResponse(BaseModel):
    """Una entrada del log de auditoría."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    fecha_hora: datetime
    actor_id: uuid.UUID
    impersonado_id: Optional[uuid.UUID] = None
    materia_id: Optional[uuid.UUID] = None
    accion: str
    filas_afectadas: Optional[int] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None


class LogCompletoResponse(BaseModel):
    """Respuesta paginada del endpoint GET /auditoria/log."""

    model_config = ConfigDict(extra="forbid")

    total: int
    page: int
    page_size: int
    items: list[AuditLogEntryResponse]


class AccionPorDiaItem(BaseModel):
    """Cantidad de acciones de auditoría en un día específico."""

    model_config = ConfigDict(extra="forbid")

    fecha: date
    cantidad: int


class AccionesPorDiaResponse(BaseModel):
    """Respuesta del endpoint GET /auditoria/acciones-por-dia."""

    model_config = ConfigDict(extra="forbid")

    items: list[AccionPorDiaItem]


class EstadoComunicacionesDocenteItem(BaseModel):
    """Distribución de estados de comunicaciones de un docente en una materia."""

    model_config = ConfigDict(extra="forbid")

    enviado_por: uuid.UUID
    materia_id: uuid.UUID
    estado: str
    cantidad: int


class EstadoComunicacionesResponse(BaseModel):
    """Respuesta del endpoint GET /auditoria/comunicaciones-por-docente."""

    model_config = ConfigDict(extra="forbid")

    items: list[EstadoComunicacionesDocenteItem]


class InteraccionDocenteMateriaItem(BaseModel):
    """Conteo de acciones de un docente sobre una materia, desglosado por código de acción."""

    model_config = ConfigDict(extra="forbid")

    actor_id: uuid.UUID
    materia_id: uuid.UUID
    accion: str
    cantidad: int


class InteraccionesResponse(BaseModel):
    """Respuesta del endpoint GET /auditoria/interacciones."""

    model_config = ConfigDict(extra="forbid")

    items: list[InteraccionDocenteMateriaItem]


class UltimasAccionesResponse(BaseModel):
    """Respuesta del endpoint GET /auditoria/ultimas-acciones."""

    model_config = ConfigDict(extra="forbid")

    limite_aplicado: int
    items: list[AuditLogEntryResponse]
