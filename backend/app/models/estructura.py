import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class EstadoEntidad(str, enum.Enum):
    activa = "activa"
    inactiva = "inactiva"


class Carrera(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "carrera"

    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[EstadoEntidad] = mapped_column(
        Enum(EstadoEntidad, name="estadoentidad"), nullable=False, default=EstadoEntidad.activa
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_carrera_tenant_codigo"),
        Index("ix_carrera_tenant", "tenant_id"),
    )


class Cohorte(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "cohorte"

    carrera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carrera.id", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    vig_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vig_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[EstadoEntidad] = mapped_column(
        Enum(EstadoEntidad, name="estadoentidad"), nullable=False, default=EstadoEntidad.activa
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "carrera_id", "nombre", name="uq_cohorte_tenant_carrera_nombre"),
        Index("ix_cohorte_tenant", "tenant_id"),
        Index("ix_cohorte_carrera", "carrera_id"),
    )


class Materia(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "materia"

    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[EstadoEntidad] = mapped_column(
        Enum(EstadoEntidad, name="estadoentidad"), nullable=False, default=EstadoEntidad.activa
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_materia_tenant_codigo"),
        Index("ix_materia_tenant", "tenant_id"),
    )


class InstanciaDictado(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "instancia_dictado"

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materia.id", ondelete="RESTRICT"), nullable=False
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorte.id", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    periodo: Mapped[str] = mapped_column(String(20), nullable=False)
    plus_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[EstadoEntidad] = mapped_column(
        Enum(EstadoEntidad, name="estadoentidad"), nullable=False, default=EstadoEntidad.activa
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "materia_id", "cohorte_id", "periodo",
            name="uq_instancia_tenant_materia_cohorte_periodo",
        ),
        Index("ix_instancia_tenant", "tenant_id"),
        Index("ix_instancia_cohorte", "cohorte_id"),
        Index("ix_instancia_materia", "materia_id"),
    )
