import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.estructura import EstadoEntidad


# ── Carrera ───────────────────────────────────────────────────────────────────

class CarreraCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str
    nombre: str


class CarreraUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: Optional[str] = None
    estado: Optional[EstadoEntidad] = None


class CarreraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    codigo: str
    nombre: str
    estado: EstadoEntidad


# ── Cohorte ───────────────────────────────────────────────────────────────────

class CohorteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    carrera_id: uuid.UUID
    nombre: str
    anio: int
    vig_desde: date
    vig_hasta: Optional[date] = None


class CohorteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: Optional[str] = None
    anio: Optional[int] = None
    vig_desde: Optional[date] = None
    vig_hasta: Optional[date] = None
    estado: Optional[EstadoEntidad] = None


class CohorteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    carrera_id: uuid.UUID
    nombre: str
    anio: int
    vig_desde: date
    vig_hasta: Optional[date]
    estado: EstadoEntidad


# ── Materia ───────────────────────────────────────────────────────────────────

class MateriaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str
    nombre: str


class MateriaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: Optional[str] = None
    estado: Optional[EstadoEntidad] = None


class MateriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    codigo: str
    nombre: str
    estado: EstadoEntidad


# ── InstanciaDictado ──────────────────────────────────────────────────────────

class InstanciaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    nombre: str
    periodo: str


class InstanciaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: Optional[str] = None
    estado: Optional[EstadoEntidad] = None


class InstanciaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    nombre: str
    periodo: str
    estado: EstadoEntidad
