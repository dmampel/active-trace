"""Modelos SQLAlchemy para SlotEncuentro e InstanciaEncuentro (C-13).

SlotEncuentro: serie de encuentros sincrónicos (recurrente o único).
    - Recurrente: cant_semanas > 0 y fecha_unica IS NULL
    - Único: fecha_unica IS NOT NULL y cant_semanas IS NULL
    La exclusividad se valida en la capa Pydantic (RN-13); a nivel DB ambos
    campos son nullable para permitir ambas variantes.

InstanciaEncuentro: ocurrencia individual de un slot, editable sin tocar
    el slot ni las demás instancias de la misma serie (RN-14).
    FK a slot_encuentro nullable: si el slot se soft-deletea, la instancia
    mantiene su historial.

Reglas duras cumplidas:
- Soft delete (deleted_at) en ambas entidades.
- tenant_id en ambas entidades (row-level isolation).
- Enums Python mapeados a native PG enums.
"""

import enum
import uuid
from datetime import date, time

from sqlalchemy import Date, Enum, ForeignKey, Index, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class DiaSemana(str, enum.Enum):
    Lunes = "Lunes"
    Martes = "Martes"
    Miercoles = "Miercoles"
    Jueves = "Jueves"
    Viernes = "Viernes"
    Sabado = "Sabado"
    Domingo = "Domingo"


class EstadoInstanciaEncuentro(str, enum.Enum):
    Programado = "Programado"
    Realizado = "Realizado"
    Cancelado = "Cancelado"


class SlotEncuentro(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Serie recurrente o encuentro único vinculado a una asignación docente.

    Invariantes:
    - Exactamente uno de (cant_semanas > 0, fecha_unica) debe estar presente.
      La validación es responsabilidad del schema Pydantic (RN-13).
    - asignacion_id proviene SIEMPRE del JWT — nunca del body HTTP.
    - Las instancias se generan en EncuentrosService.crear_slot() (D2).
    """

    __tablename__ = "slot_encuentro"

    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asignacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)

    # Recurrente
    cant_semanas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    dia_semana: Mapped[DiaSemana | None] = mapped_column(
        Enum(DiaSemana, name="diasemana"),
        nullable=True,
    )

    # Único
    fecha_unica: Mapped[date | None] = mapped_column(Date, nullable=True)

    hora: Mapped[time] = mapped_column(Time, nullable=False)
    meet_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # tenant_id indexado via TenantMixin (index=True en la columna)
        # asignacion_id indexado via index=True en mapped_column arriba
    )


class InstanciaEncuentro(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Ocurrencia individual de un slot de encuentro.

    Invariantes:
    - Editable por instancia sin tocar el slot ni las demás instancias (RN-14).
    - slot_id nullable: el slot puede ser soft-deleted sin perder el historial.
    - tenant_id duplicado del slot para queries directas sobre instancias.
    """

    __tablename__ = "instancia_encuentro"

    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("slot_encuentro.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora: Mapped[time] = mapped_column(Time, nullable=False)
    estado: Mapped[EstadoInstanciaEncuentro] = mapped_column(
        Enum(EstadoInstanciaEncuentro, name="estadoinstanciaencuentro"),
        nullable=False,
        default=EstadoInstanciaEncuentro.Programado,
    )
    meet_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # tenant_id indexado via TenantMixin (index=True en la columna)
        # slot_id indexado via index=True en mapped_column arriba
        Index("ix_instancia_encuentro_fecha", "fecha"),
    )
