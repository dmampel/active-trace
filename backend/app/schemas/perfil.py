"""Schemas Pydantic v2 para perfil propio (C-20).

Reglas:
- extra='forbid' en todos los schemas.
- PerfilRead: incluye cuil descifrado (titular leyendo su propio dato).
- PerfilUpdate: SIN campo cuil (solo lectura para el titular → 422 si se envía).
  modalidad_cobro ('factura'/'liquidacion') mapea al booleano facturador del modelo.
"""
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.estructura import EstadoEntidad


class PerfilRead(BaseModel):
    """DTO de lectura del propio perfil. Incluye PII descifrada del titular."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    # PII descifrada — solo para el propio titular
    dni: Optional[str] = None
    cuil: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    legajo: Optional[str] = None
    legajo_profesional: Optional[str] = None
    facturador: bool
    estado: EstadoEntidad


class PerfilUpdate(BaseModel):
    """DTO de actualización del propio perfil.

    cuil NO está declarado → extra='forbid' retorna 422 si se envía.
    modalidad_cobro ('factura'/'liquidacion') es un alias legible de 'facturador'.
    """

    model_config = ConfigDict(extra="forbid")

    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[str] = None
    # PII editable — el Service cifra antes de persistir
    dni: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    legajo_profesional: Optional[str] = None
    # Alias legible de 'facturador': 'factura' → True, 'liquidacion' → False
    modalidad_cobro: Optional[Literal["factura", "liquidacion"]] = None
