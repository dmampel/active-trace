"""Modelos SQLAlchemy para calificaciones y configuración de umbral (C-10).

Calificacion: nota de un alumno en una actividad evaluable, vinculada a su
              EntradaPadron (FK CASCADE) y scopeada por tenant.
UmbralMateria: umbral de aprobación configurado por asignación docente.

Invariantes de dominio:
- `aprobado` NO es columna — se deriva en la función pura `derivar_aprobado`
  (domain/aprobado.py). El Service resuelve el umbral vigente y llama la función.
- `materia_id` es UUID indexado sin FK dura (sigue patrón C-09 / decisión D1).
  FK dura se posterga hasta que PA-01 (Materia vs InstanciaDictado) se resuelva.
- `UmbralMateria.asignacion_id` sí tiene FK dura a `asignacion.id`.
- Soft delete siempre; nunca hard delete.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class OrigenCalificacion(str, enum.Enum):
    IMPORTADO = "Importado"
    MANUAL = "Manual"


class Calificacion(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Nota de un alumno en una actividad evaluable.

    - `entrada_padron_id` → FK con CASCADE al alumno del padrón.
    - `materia_id` → UUID indexado, sin FK dura (D1).
    - `nota_numerica` y `nota_textual` son mutuamente excluyentes en lo conceptual,
      pero el modelo acepta ambas (precedencia numérica al derivar aprobado, D2).
    - `aprobado` NO se persiste (D2).
    """

    __tablename__ = "calificacion"

    entrada_padron_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entrada_padron.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    actividad: Mapped[str] = mapped_column(String(500), nullable=False)
    nota_numerica: Mapped[float | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
    )
    nota_textual: Mapped[str | None] = mapped_column(String(500), nullable=True)
    origen: Mapped[OrigenCalificacion] = mapped_column(
        Enum(OrigenCalificacion, name="origencalificacion"),
        nullable=False,
    )
    importado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        # ix_calificacion_tenant_id ya creado por TenantMixin (index=True)
        # ix_calificacion_materia_id y entrada_padron_id creados por index=True arriba
        Index(
            "ix_calificacion_tenant_materia",
            "tenant_id",
            "materia_id",
        ),
    )


class UmbralMateria(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Umbral de aprobación configurado por asignación docente en una materia.

    - Anclado a `asignacion_id` (FK) + `materia_id` (UUID indexado sin FK).
    - Scope aislado: cada asignación tiene su propio umbral (RN-03 + RN-04 análogo).
    - Si no existe para la asignación, el Service usa el defecto del tenant (60%).
    """

    __tablename__ = "umbral_materia"

    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asignacion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    umbral_pct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )
    valores_aprobatorios: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    __table_args__ = (
        # ix_umbral_materia_tenant_id creado por TenantMixin (index=True)
        # ix_umbral_materia_asignacion_id y materia_id creados por index=True arriba
        Index(
            "ix_umbral_materia_tenant_asignacion_materia",
            "tenant_id",
            "asignacion_id",
            "materia_id",
            unique=True,
        ),
    )
