"""Modelos SQLAlchemy para el módulo de programas de materia (C-17).

Entidades:
- ProgramaMateria: syllabus/programa vinculado a (materia, carrera, cohorte).
  Un programa por contexto académico (UniqueConstraint).

Reglas duras cumplidas:
- Soft delete (deleted_at) via SoftDeleteMixin.
- tenant_id en todas las entidades (row-level isolation) via TenantMixin.
- referencia_archivo es texto opaco — sin upload real (D1 del design).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class ProgramaMateria(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Programa (syllabus) de una materia en un contexto académico específico.

    Invariantes:
    - Un único programa por (tenant_id, materia_id, carrera_id, cohorte_id).
    - referencia_archivo es un texto libre opaco (URL, path, ID externo).
    - cargado_at registra cuándo se subió la referencia.
    - tenant_id viene SIEMPRE del JWT — nunca del body HTTP.
    - Soft delete: deleted_at se setea al eliminar; la fila persiste para auditoría.
    """

    __tablename__ = "programa_materia"

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    carrera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carrera.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    referencia_archivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    cargado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "materia_id", "carrera_id", "cohorte_id",
            name="uq_programa_materia_contexto",
        ),
        Index(
            "ix_programa_materia_tenant_materia_carrera_cohorte",
            "tenant_id", "materia_id", "carrera_id", "cohorte_id",
        ),
    )
