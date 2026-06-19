"""Modelos SQLAlchemy para el módulo de avisos y acknowledgment (C-15).

Entidades:
- Aviso: aviso institucional con segmentación de audiencia y ventana de vigencia.
- AcknowledgmentAviso: confirmación de lectura por usuario (idempotente via unique constraint).

Reglas duras cumplidas:
- Soft delete (deleted_at) en Aviso.
- tenant_id en Aviso (row-level isolation).
- Enums Python mapeados a native PG enums.
- UniqueConstraint (aviso_id, usuario_id) en AcknowledgmentAviso.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class AlcanceAviso(str, enum.Enum):
    Global = "Global"
    PorMateria = "PorMateria"
    PorCohorte = "PorCohorte"
    PorRol = "PorRol"


class SeveridadAviso(str, enum.Enum):
    Info = "Info"
    Advertencia = "Advertencia"
    Critico = "Critico"


class Aviso(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Aviso institucional segmentado por audiencia.

    Invariantes:
    - alcance define cómo se segmenta la audiencia:
        Global      → todos los usuarios del tenant
        PorMateria  → materia_id MUST NOT be NULL
        PorCohorte  → cohorte_id MUST NOT be NULL
        PorRol      → rol_destino MUST NOT be NULL
    - tenant_id viene SIEMPRE del JWT — nunca del body HTTP.
    - Soft delete: deleted_at se setea al eliminar; la fila persiste para auditoría.
    - activo=false hace que el aviso no aparezca en el feed (control editorial).
    """

    __tablename__ = "aviso"

    alcance: Mapped[AlcanceAviso] = mapped_column(
        Enum(AlcanceAviso, name="alcanceaviso"),
        nullable=False,
    )
    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    cohorte_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    rol_destino: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severidad: Mapped[SeveridadAviso] = mapped_column(
        Enum(SeveridadAviso, name="severidadaviso"),
        nullable=False,
        default=SeveridadAviso.Info,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    inicio_en: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    fin_en: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requiere_ack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relación inversa — no lazy-load por defecto
    acknowledgments: Mapped[list[AcknowledgmentAviso]] = relationship(
        "AcknowledgmentAviso",
        back_populates="aviso",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    __table_args__ = (
        # ix_aviso_tenant_id already created by TenantMixin (index=True on tenant_id)
        Index("ix_aviso_alcance", "alcance"),
        Index("ix_aviso_feed", "tenant_id", "alcance", "activo", "inicio_en"),
    )


class AcknowledgmentAviso(Base, UUIDMixin):
    """Confirmación de lectura de un aviso por un usuario.

    Idempotente: el unique constraint (aviso_id, usuario_id) garantiza que
    nunca haya más de un registro por par. El upsert usa ON CONFLICT DO NOTHING.
    Sin tenant_id propio — hereda el aislamiento via aviso → tenant.
    Sin soft delete — la confirmación es inmutable (auditoría natural).
    """

    __tablename__ = "acknowledgment_aviso"

    aviso_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aviso.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    confirmado_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    aviso: Mapped[Aviso] = relationship("Aviso", back_populates="acknowledgments")

    __table_args__ = (
        UniqueConstraint("aviso_id", "usuario_id", name="uix_ack_aviso_usuario"),
        Index("ix_ack_aviso_aviso_id", "aviso_id"),
        Index("ix_ack_aviso_usuario_id", "usuario_id"),
    )
