"""Modelos SQLAlchemy para el módulo de liquidaciones y honorarios (C-18).

Entidades:
- SalarioBase: grilla salarial base por rol con vigencia temporal
- SalarioPlus: incremento adicional por clave × rol con vigencia temporal
- Liquidacion: importe calculado por (cohorte × período × docente)
- Factura: comprobante de docente monotributista (facturante)

Governance: CRÍTICO — calcula y congela pagos reales a docentes.
Reglas:
- Multi-tenant: todos los modelos llevan tenant_id (TenantMixin).
- Soft delete: todos llevan deleted_at (SoftDeleteMixin).
- Inmutabilidad de Liquidacion cerrada: garantizada en el Service, no en trigger DB.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class EstadoLiquidacion(str, enum.Enum):
    abierta = "Abierta"
    cerrada = "Cerrada"


class EstadoFactura(str, enum.Enum):
    pendiente = "Pendiente"
    abonada = "Abonada"


class SalarioBase(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Salario base por rol con vigencia temporal.

    Un rol puede tener un solo SalarioBase vigente en un período dado.
    El Service valida solapamiento antes de persistir (D3).
    """

    __tablename__ = "salario_base"

    rol: Mapped[str] = mapped_column(String(50), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        Index("ix_salario_base_tenant", "tenant_id"),
        Index("ix_salario_base_rol", "tenant_id", "rol"),
    )


class SalarioPlus(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Plus adicional por clave × rol con vigencia temporal.

    `grupo` es la clave de Plus configurada libremente por el ADMIN del tenant
    (PA-22 cerrada: texto libre, no catálogo fijo).
    Distintas claves pueden coexistir sin restricción de solapamiento.
    """

    __tablename__ = "salario_plus"

    grupo: Mapped[str] = mapped_column(Text, nullable=False)   # clave Plus (e.g. "PROG")
    rol: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        Index("ix_salario_plus_tenant", "tenant_id"),
        Index("ix_salario_plus_grupo_rol", "tenant_id", "grupo", "rol"),
    )


class Liquidacion(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Liquidación de honorarios por (cohorte × período × docente).

    Una vez en estado Cerrada, el Service rechaza cualquier modificación (RN-22).
    `comisiones` guarda snapshot JSON de las comisiones del docente en el período.
    """

    __tablename__ = "liquidacion"

    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorte.id", ondelete="RESTRICT"), nullable=False
    )
    periodo: Mapped[str] = mapped_column(String(20), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    rol: Mapped[str] = mapped_column(String(50), nullable=False)
    comisiones: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    monto_base: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    monto_plus: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    es_nexo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excluido_por_factura: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estado: Mapped[EstadoLiquidacion] = mapped_column(
        Enum(EstadoLiquidacion, name="estadoliquidacion"),
        nullable=False,
        default=EstadoLiquidacion.abierta,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "cohorte_id", "periodo", "usuario_id",
            name="uq_liquidacion_tenant_cohorte_periodo_usuario",
        ),
        Index("ix_liquidacion_tenant", "tenant_id"),
        Index("ix_liquidacion_cohorte_periodo", "cohorte_id", "periodo"),
        Index("ix_liquidacion_usuario", "usuario_id"),
    )


class Factura(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Factura de docente monotributista (facturante).

    Entidad independiente — sin FK a Liquidacion (D5).
    El campo `excluido_por_factura` en Liquidacion maneja la separación.
    """

    __tablename__ = "factura"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    periodo: Mapped[str] = mapped_column(String(20), nullable=False)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    referencia_archivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    tamano_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado: Mapped[EstadoFactura] = mapped_column(
        Enum(EstadoFactura, name="estadofactura"),
        nullable=False,
        default=EstadoFactura.pendiente,
    )
    cargada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abonada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_factura_tenant", "tenant_id"),
        Index("ix_factura_usuario", "usuario_id"),
        Index("ix_factura_periodo", "tenant_id", "periodo"),
    )
