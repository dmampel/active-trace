"""Modelos SQLAlchemy para el módulo de evaluaciones y coloquios (C-14).

Entidades:
- Evaluacion: convocatoria de coloquio/evaluación con cupos_por_dia JSONB.
- EvaluacionAlumno: tabla asociativa de alumnos habilitados a una convocatoria.
- ReservaEvaluacion: turno reservado por un ALUMNO (Activa/Cancelada).
- ResultadoEvaluacion: nota final registrada por COORDINADOR/ADMIN.
- FechaAcademica: calendarización de instancias evaluativas por materia × cohorte.

Reglas duras cumplidas:
- Soft delete (deleted_at) en Evaluacion y FechaAcademica.
- tenant_id en todas las entidades (row-level isolation).
- Enums Python mapeados a native PG enums.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class TipoEvaluacion(str, enum.Enum):
    Coloquio = "Coloquio"
    Parcial = "Parcial"
    Recuperatorio = "Recuperatorio"
    TP = "TP"


class EstadoReserva(str, enum.Enum):
    Activa = "Activa"
    Cancelada = "Cancelada"


class TipoFechaAcademica(str, enum.Enum):
    Parcial = "Parcial"
    TP = "TP"
    Coloquio = "Coloquio"
    Recuperatorio = "Recuperatorio"


class Evaluacion(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Convocatoria de evaluación con cupos por turno (JSONB).

    Invariantes:
    - cupos_por_dia: dict {fecha_iso: cupos_disponibles}. Actualizable atómicamente via SQL.
    - tenant_id viene SIEMPRE del JWT — nunca del body HTTP.
    - Soft delete: deleted_at se setea al eliminar; la fila persiste para auditoría.
    """

    __tablename__ = "evaluacion"

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[TipoEvaluacion] = mapped_column(
        Enum(TipoEvaluacion, name="tipoevaluacion"),
        nullable=False,
    )
    instancia: Mapped[str] = mapped_column(String(255), nullable=False)
    cupos_por_dia: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    __table_args__ = (
        Index("ix_evaluacion_materia_cohorte", "materia_id", "cohorte_id"),
    )


class EvaluacionAlumno(Base, TenantMixin):
    """Tabla asociativa: alumnos habilitados/convocados para una Evaluacion.

    Sin timestamps ni soft delete — es una lista de habilitación.
    Si se necesita auditoría de quién fue convocado, el AuditLog la captura.
    """

    __tablename__ = "evaluacion_alumno"

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    __table_args__ = (
        Index("ix_evaluacion_alumno_evaluacion", "evaluacion_id"),
        Index("ix_evaluacion_alumno_alumno", "alumno_id"),
        Index("ix_evaluacion_alumno_tenant", "tenant_id"),
    )


class ReservaEvaluacion(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Turno reservado por un ALUMNO en una convocatoria.

    estado Activa/Cancelada. La cancelación libera cupo via SQL atómico.
    Sin soft delete propio — el estado Cancelada es el mecanismo de "eliminación".
    """

    __tablename__ = "reserva_evaluacion"

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha: Mapped[str] = mapped_column(String(10), nullable=False)  # ISO date: YYYY-MM-DD
    estado: Mapped[EstadoReserva] = mapped_column(
        Enum(EstadoReserva, name="estadoreserva"),
        nullable=False,
        default=EstadoReserva.Activa,
    )

    __table_args__ = (
        Index("ix_reserva_evaluacion_tenant", "tenant_id"),
        Index("ix_reserva_evaluacion_evaluacion", "evaluacion_id"),
        Index("ix_reserva_evaluacion_alumno", "alumno_id"),
    )


class ResultadoEvaluacion(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Nota final de un alumno en una Evaluacion.

    nota_final es texto para soportar "Aprobado", "8.5", "Desaprobado", etc.
    Upsert por (evaluacion_id, alumno_id) via ON CONFLICT DO UPDATE.
    """

    __tablename__ = "resultado_evaluacion"

    evaluacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    alumno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nota_final: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("evaluacion_id", "alumno_id", name="uq_resultado_evaluacion_alumno"),
        Index("ix_resultado_evaluacion_tenant", "tenant_id"),
        Index("ix_resultado_evaluacion_evaluacion", "evaluacion_id"),
    )


class FechaAcademica(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Calendarización de instancias evaluativas por materia × cohorte.

    Módulo independiente de Evaluacion — es informativo, no operativo.
    Registra cuándo ocurren parciales, TPs, coloquios, etc.
    """

    __tablename__ = "fecha_academica"

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[TipoFechaAcademica] = mapped_column(
        Enum(TipoFechaAcademica, name="tipofechaacademica"),
        nullable=False,
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha: Mapped[str] = mapped_column(String(10), nullable=False)  # ISO date YYYY-MM-DD
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (  # type: ignore[assignment]
        Index("ix_fecha_academica_tenant", "tenant_id"),
        Index("ix_fecha_academica_materia_cohorte", "materia_id", "cohorte_id"),
    )
