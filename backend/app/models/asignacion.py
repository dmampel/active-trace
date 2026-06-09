import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class RolDominio(str, enum.Enum):
    PROFESOR = "PROFESOR"
    TUTOR = "TUTOR"
    COORDINADOR = "COORDINADOR"
    NEXO = "NEXO"
    ADMIN = "ADMIN"
    FINANZAS = "FINANZAS"


class Asignacion(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Asignación contextual: usuario ↔ rol académico con vigencia y jerarquía.

    Complementa `user_rol` (rol global de tenant) con un rol acotado a un
    contexto académico (materia / carrera / cohorte / comisiones).
    `estado_vigencia` NO se almacena — se deriva en el Service.
    """

    __tablename__ = "asignacion"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rol: Mapped[RolDominio] = mapped_column(
        Enum(RolDominio, name="roldominio"), nullable=False
    )

    # Contexto académico — todos nullables (asignación global si todos son null)
    materia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materia.id", ondelete="RESTRICT"), nullable=True
    )
    carrera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carrera.id", ondelete="RESTRICT"), nullable=True
    )
    cohorte_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorte.id", ondelete="RESTRICT"), nullable=True
    )

    # Lista de comisiones (texto), placeholder hasta C-08
    comisiones: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Jerarquía — quién es responsable de esta asignación (nullable)
    responsable_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="RESTRICT"), nullable=True
    )

    # Vigencia
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        Index("ix_asignacion_tenant", "tenant_id"),
        Index("ix_asignacion_usuario", "usuario_id"),
    )
