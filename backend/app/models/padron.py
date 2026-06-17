"""Modelos SQLAlchemy para el padrón de alumnos.

VersionPadron: contenedor versionado (materia × cohorte × cargado_por × timestamp).
EntradaPadron: una fila del padrón — un alumno por fila.

Invariantes de dominio:
- Por cada (tenant_id, materia_id, cohorte_id) solo puede haber una versión activa.
  Se garantiza en la capa de repositorio (transacción atómica), no con un índice
  unique DB (porque activa puede ser False en las anteriores).
- email_enc: campo PII almacenado cifrado AES-256-GCM. El Service cifra/descifra;
  el Repository nunca toca el valor en texto plano.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin, utc_now


class VersionPadron(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Contenedor versionado de padrón para una (materia, cohorte) de un tenant."""

    __tablename__ = "version_padron"

    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    cohorte_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    cargado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    cargado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        # Índice para queries frecuentes: obtener versión activa por materia/cohorte/tenant
        Index(
            "ix_version_padron_tenant_materia_cohorte_activa",
            "tenant_id",
            "materia_id",
            "cohorte_id",
            "activa",
        ),
    )


class EntradaPadron(Base, UUIDMixin, TimestampMixin):
    """Una entrada (alumno) dentro de una VersionPadron."""

    __tablename__ = "entrada_padron"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("version_padron.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Referencia opcional al usuario del sistema (si el alumno tiene cuenta)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(255), nullable=False)
    # PII cifrada AES-256-GCM. El Service cifra/descifra; este campo NUNCA se lee/escribe
    # en texto plano fuera del Service.
    email_enc: Mapped[str] = mapped_column(String(512), nullable=False)
    comision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    regional: Mapped[str | None] = mapped_column(String(100), nullable=True)
