"""Schemas Pydantic v2 para mensajería interna (C-20).

Reglas:
- extra='forbid' en todos los schemas.
- Separados completamente de comunicacion.py (C-12).
- Un hilo tiene dos participantes: creador + destinatario.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class HiloRead(BaseModel):
    """DTO de lectura de un hilo de mensajes."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    asunto: str
    creado_por: uuid.UUID
    created_at: datetime


class MensajeRead(BaseModel):
    """DTO de lectura de un mensaje dentro de un hilo."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    hilo_id: uuid.UUID
    autor_id: uuid.UUID
    destinatario_id: uuid.UUID
    cuerpo: str
    leido: bool
    created_at: datetime


class HiloConMensajesRead(BaseModel):
    """DTO de lectura de un hilo con todos sus mensajes."""

    model_config = ConfigDict(extra="forbid")

    hilo: HiloRead
    mensajes: List[MensajeRead]


class NuevoHiloCreate(BaseModel):
    """Schema para crear un nuevo hilo con su primer mensaje.

    extra='forbid': cualquier campo no declarado → 422.
    """

    model_config = ConfigDict(extra="forbid")

    destinatario_id: uuid.UUID
    asunto: str
    cuerpo: str


class RespuestaCreate(BaseModel):
    """Schema para responder dentro de un hilo existente.

    extra='forbid': cualquier campo no declarado → 422.
    """

    model_config = ConfigDict(extra="forbid")

    cuerpo: str
