"""Schemas Pydantic v2 para el módulo de liquidaciones y honorarios (C-18).

Todos los schemas de request usan extra='forbid' para rechazar campos no declarados.
tenant_id nunca se acepta en requests — viene siempre del JWT.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.liquidacion import EstadoFactura, EstadoLiquidacion


# ────────────────────────────────────────────────────────────────────────────────
# Salario Base
# ────────────────────────────────────────────────────────────────────────────────


class SalarioBaseCreate(BaseModel):
    """Payload para crear un salario base.

    tenant_id viene del JWT — no se acepta en el body.
    """

    model_config = ConfigDict(extra="forbid")

    rol: str
    monto: Decimal
    desde: date
    hasta: Optional[date] = None


class SalarioBaseUpdate(BaseModel):
    """Campos actualizables de un salario base (solo monto y hasta)."""

    model_config = ConfigDict(extra="forbid")

    monto: Optional[Decimal] = None
    hasta: Optional[date] = None


class SalarioBaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    rol: str
    monto: Decimal
    desde: date
    hasta: Optional[date]
    created_at: datetime
    updated_at: datetime


# ────────────────────────────────────────────────────────────────────────────────
# Salario Plus
# ────────────────────────────────────────────────────────────────────────────────


class SalarioPlusCreate(BaseModel):
    """Payload para crear un plus salarial.

    `grupo` es la clave de Plus libre (e.g. "PROG", "BD").
    """

    model_config = ConfigDict(extra="forbid")

    grupo: str
    rol: str
    descripcion: Optional[str] = None
    monto: Decimal
    desde: date
    hasta: Optional[date] = None


class SalarioPlusUpdate(BaseModel):
    """Campos actualizables de un plus salarial."""

    model_config = ConfigDict(extra="forbid")

    monto: Optional[Decimal] = None
    descripcion: Optional[str] = None
    hasta: Optional[date] = None


class SalarioPlusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    grupo: str
    rol: str
    descripcion: Optional[str]
    monto: Decimal
    desde: date
    hasta: Optional[date]
    created_at: datetime
    updated_at: datetime


# ────────────────────────────────────────────────────────────────────────────────
# Grilla salarial (respuesta combinada)
# ────────────────────────────────────────────────────────────────────────────────


class GrillaSalarialResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base: list[SalarioBaseResponse]
    plus: list[SalarioPlusResponse]


# ────────────────────────────────────────────────────────────────────────────────
# Liquidacion
# ────────────────────────────────────────────────────────────────────────────────


class LiquidacionCalcularRequest(BaseModel):
    """Request para calcular/recalcular liquidaciones de un período."""

    model_config = ConfigDict(extra="forbid")

    cohorte_id: uuid.UUID
    periodo: str   # e.g. "2026-03"


class ComisionDetalle(BaseModel):
    """Snapshot de una comisión incluida en la liquidación."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    instancia_id: uuid.UUID
    plus_key: Optional[str]


class LiquidacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    cohorte_id: uuid.UUID
    periodo: str
    usuario_id: uuid.UUID
    rol: str
    monto_base: Decimal
    monto_plus: Decimal
    total: Decimal
    es_nexo: bool
    excluido_por_factura: bool
    estado: EstadoLiquidacion
    created_at: datetime
    updated_at: datetime


class LiquidacionDetalle(LiquidacionResponse):
    """Versión extendida con snapshot de comisiones y claves activas."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    comisiones: list[Any]
    claves_activas: list[str]


class DocenteOmitido(BaseModel):
    """Docente excluido del cálculo por falta de datos bancarios."""

    model_config = ConfigDict(extra="forbid")

    usuario_id: uuid.UUID
    motivo: str


class LiquidacionCalcularResponse(BaseModel):
    """Resultado del cálculo de un período."""

    model_config = ConfigDict(extra="forbid")

    creadas: int
    actualizadas: int
    liquidaciones: list[LiquidacionResponse]
    omitidos: list[DocenteOmitido]


# Vista segmentada


class LiquidacionVistaPeriodo(BaseModel):
    """Vista paginada y segmentada de liquidaciones de un período."""

    model_config = ConfigDict(extra="forbid")

    cohorte_id: uuid.UUID
    periodo: str
    general: list[LiquidacionResponse]
    nexo: list[LiquidacionResponse]
    facturantes: list[LiquidacionResponse]
    total_sin_factura: Decimal
    total_con_factura: Decimal


# ────────────────────────────────────────────────────────────────────────────────
# Factura
# ────────────────────────────────────────────────────────────────────────────────


class FacturaCreate(BaseModel):
    """Payload para cargar una factura de docente facturante."""

    model_config = ConfigDict(extra="forbid")

    usuario_id: uuid.UUID
    periodo: str
    detalle: Optional[str] = None
    referencia_archivo: Optional[str] = None
    tamano_kb: Optional[int] = None


class FacturaPatchRequest(BaseModel):
    """Payload para actualizar el estado de una factura (Pendiente → Abonada)."""

    model_config = ConfigDict(extra="forbid")

    estado: EstadoFactura


class FacturaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    periodo: str
    detalle: Optional[str]
    referencia_archivo: Optional[str]
    tamano_kb: Optional[int]
    estado: EstadoFactura
    cargada_at: Optional[datetime]
    abonada_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
