"""Schemas Pydantic v2 para el módulo de comunicaciones salientes (C-12).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.
`destinatario` nunca se expone en texto plano — solo como `destinatario_masked`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.comunicacion import EstadoComunicacion


# ── Requests ─────────────────────────────────────────────────────────────────


class ComunicacionPreviewRequest(BaseModel):
    """Request para previsualizar un mensaje con variables de sustitución."""

    model_config = ConfigDict(extra="forbid")

    asunto: str
    cuerpo: str
    contexto: dict  # variables de sustitución: {"alumno.nombre": "Ana", ...}


class ComunicacionEnviarRequest(BaseModel):
    """Request para encolar mensajes salientes (individual o masivo)."""

    model_config = ConfigDict(extra="forbid")

    destinatarios: list[str]  # lista de emails
    asunto: str
    cuerpo: str
    materia_id: uuid.UUID
    lote_descripcion: Optional[str] = None

    @field_validator("destinatarios")
    @classmethod
    def al_menos_un_destinatario(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("Se requiere al menos un destinatario")
        return v


class LoteAccionRequest(BaseModel):
    """Request vacío para acciones sobre un lote (la acción la define el endpoint)."""

    model_config = ConfigDict(extra="forbid")


# ── Responses ─────────────────────────────────────────────────────────────────


class ComunicacionPreviewResponse(BaseModel):
    """Respuesta de preview: mensaje renderizado con variables sustituidas."""

    model_config = ConfigDict(extra="forbid")

    asunto_renderizado: str
    cuerpo_renderizado: str
    warnings: list[str]  # variables no resueltas


class ComunicacionEnviarResponse(BaseModel):
    """Respuesta al encolar mensajes."""

    model_config = ConfigDict(extra="forbid")

    lote_id: Optional[uuid.UUID] = None  # None para envío individual
    ids_encolados: list[uuid.UUID]
    total: int


class ComunicacionResponse(BaseModel):
    """Representación pública de una Comunicacion.

    `destinatario` nunca se expone en claro — solo `destinatario_masked`.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    enviado_por: uuid.UUID
    materia_id: uuid.UUID
    destinatario_masked: str  # e.g. "a***@dominio.com"
    asunto: str
    cuerpo: str
    estado: EstadoComunicacion
    lote_id: Optional[uuid.UUID] = None
    enviado_at: Optional[datetime] = None
    aprobado_at: Optional[datetime] = None
    created_at: datetime
    deleted_at: Optional[datetime] = None


class LoteAccionResponse(BaseModel):
    """Respuesta a una acción sobre un lote."""

    model_config = ConfigDict(extra="forbid")

    lote_id: uuid.UUID
    afectados: int
    estado_nuevo: str
