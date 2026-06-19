"""Modelos SQLAlchemy para el módulo de tareas internas (C-16).

Entidades:
- Tarea: tarea interna con ciclo de vida pendiente → en_progreso → resuelta/cancelada.
- ComentarioTarea: comentario append-only en el hilo de una tarea.

Reglas duras cumplidas:
- Soft delete (deleted_at) en Tarea (ComentarioTarea es append-only, sin soft-delete).
- tenant_id en ambas entidades (row-level isolation).
- Enum Python mapeado a native PG enum.
- contexto_id como UUID nullable sin FK tipada (D2).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class EstadoTarea(str, enum.Enum):
    pendiente = "pendiente"
    en_progreso = "en_progreso"
    resuelta = "resuelta"
    cancelada = "cancelada"


class Tarea(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Tarea interna asignada entre miembros del tenant.

    Invariantes:
    - Estado inicial siempre pendiente — nunca viene del body.
    - asignado_por y tenant_id provienen SIEMPRE del JWT.
    - Máquina de estados validada en TareaService (D1).
    - contexto_id es un UUID libre sin FK tipada (D2): puede referenciar
      cualquier entidad del dominio sin acoplamiento de schema.
    """

    __tablename__ = "tarea"

    asignado_a: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    asignado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    estado: Mapped[EstadoTarea] = mapped_column(
        Enum(EstadoTarea, name="estadotarea"),
        nullable=False,
        default=EstadoTarea.pendiente,
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    # contexto_id: referencia libre sin FK (D2)
    contexto_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    __table_args__ = (
        # Índices para queries frecuentes: mis-tareas y tareas-asignadas
        Index("ix_tarea_tenant_asignado_a_estado", "tenant_id", "asignado_a", "estado"),
        Index("ix_tarea_tenant_asignado_por_estado", "tenant_id", "asignado_por", "estado"),
    )


class ComentarioTarea(Base, UUIDMixin):
    """Comentario append-only en el hilo de una tarea.

    Sin soft-delete: los comentarios son inmutables (D4 — auditoría natural).
    Sin TimestampMixin: solo tiene creado_at, sin updated_at.
    tenant_id duplicado para queries directas sin JOIN a tarea.
    """

    __tablename__ = "comentario_tarea"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tarea_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tarea.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    creado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Índices ya creados automáticamente via index=True en mapped_column arriba
