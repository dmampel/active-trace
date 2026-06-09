"""Schemas Pydantic v2 para usuarios.

Reglas:
- extra='forbid' en todos los schemas (rechaza campos no declarados).
- UsuarioListItem: SIN PII en claro (sin dni/cuil/cbu/alias_cbu).
- UsuarioDetail: CON PII descifrada (solo para quien tiene usuarios:gestionar).
- UsuarioCreate/Update: campos PII en claro (el Service los cifra).
"""
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.estructura import EstadoEntidad


class UsuarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    # PII — el Service los cifra antes de persistir
    dni: Optional[str] = None
    cuil: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    legajo: Optional[str] = None
    legajo_profesional: Optional[str] = None
    facturador: bool = False


class UsuarioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    # PII — el Service los cifra antes de persistir
    dni: Optional[str] = None
    cuil: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    legajo: Optional[str] = None
    legajo_profesional: Optional[str] = None
    facturador: Optional[bool] = None
    estado: Optional[EstadoEntidad] = None


class UsuarioListItem(BaseModel):
    """DTO de listado: NO incluye PII cifrada (dni/cuil/cbu/alias_cbu)."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    legajo: Optional[str] = None
    legajo_profesional: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    facturador: bool
    estado: EstadoEntidad


class UsuarioDetail(BaseModel):
    """DTO de detalle administrativo: incluye PII descifrada.

    Solo para endpoints protegidos por usuarios:gestionar.
    """
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    # PII descifrada
    dni: Optional[str] = None
    cuil: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    legajo: Optional[str] = None
    legajo_profesional: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    facturador: bool
    estado: EstadoEntidad
