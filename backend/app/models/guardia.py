"""Modelo SQLAlchemy para Guardia (C-13).

Guardia: registro de atención de guardia realizada por un TUTOR.
- asignacion_id proviene SIEMPRE del JWT — nunca del body HTTP.
- horario es texto libre (ej. "14:00–14:45") según KB §decisiones abiertas.
- tenant_id para row-level isolation.
- Soft delete (deleted_at) por regla dura #13.
"""

import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class EstadoGuardia(str, enum.Enum):
    Pendiente = "Pendiente"
    Cubierta = "Cubierta"
    Ausente = "Ausente"


class Guardia(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Registro de guardia de atención por TUTOR.

    Invariantes:
    - asignacion_id proviene del JWT del usuario autenticado; nunca del request body.
    - horario es texto libre (validado not-empty en Pydantic).
    - materia_id / carrera_id / cohorte_id son referencias al contexto académico
      (no FK duras para mantener flexibilidad ante C-06).
    """

    __tablename__ = "guardia"

    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asignacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    carrera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cohorte_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    dia: Mapped[date] = mapped_column(Date, nullable=False)
    horario: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[EstadoGuardia] = mapped_column(
        Enum(EstadoGuardia, name="estadoguardia"),
        nullable=False,
        default=EstadoGuardia.Pendiente,
    )
    comentarios: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # tenant_id indexado via TenantMixin (index=True en la columna)
        # asignacion_id indexado via index=True en mapped_column arriba
        Index("ix_guardia_materia_id", "materia_id"),
        Index("ix_guardia_dia", "dia"),
        Index("ix_guardia_tenant_estado", "tenant_id", "estado"),
    )
