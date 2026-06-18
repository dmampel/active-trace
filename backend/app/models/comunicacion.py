"""Modelo SQLAlchemy para Comunicacion (C-12).

Comunicacion: mensaje saliente encolado para despacho por SMTP.
- Máquina de estados: Pendiente → Enviando → Enviado | Error | Cancelado
- `destinatario` cifrado AES-256 en app-level (columna TEXT en BD).
- `lote_id` agrupa envíos masivos — permite aprobación/cancelación por lote.
- Soft delete: deleted_at; nunca hard delete.
- Multi-tenant: tenant_id en cada fila, scoped por repositorio.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class EstadoComunicacion(str, enum.Enum):
    Pendiente = "Pendiente"
    Enviando = "Enviando"
    Enviado = "Enviado"
    Error = "Error"
    Cancelado = "Cancelado"


# Transiciones válidas de la máquina de estados
_TRANSICIONES_VALIDAS: dict[EstadoComunicacion, set[EstadoComunicacion]] = {
    EstadoComunicacion.Pendiente: {EstadoComunicacion.Enviando, EstadoComunicacion.Cancelado},
    EstadoComunicacion.Enviando: {EstadoComunicacion.Enviado, EstadoComunicacion.Error},
    EstadoComunicacion.Enviado: set(),
    EstadoComunicacion.Error: set(),
    EstadoComunicacion.Cancelado: set(),
}


def validar_transicion(origen: EstadoComunicacion, destino: EstadoComunicacion) -> None:
    """Valida que la transición de estado sea permitida.

    Raises:
        ValueError: Si la transición no es válida.
    """
    if destino not in _TRANSICIONES_VALIDAS[origen]:
        raise ValueError(
            f"Transición inválida: {origen.value} → {destino.value}. "
            f"Transiciones válidas desde {origen.value}: "
            f"{[e.value for e in _TRANSICIONES_VALIDAS[origen]]}"
        )


class Comunicacion(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Mensaje saliente encolado para despacho por SMTP.

    Invariantes:
    - `destinatario` es AES-256 cifrado — nunca se expone en texto plano en API.
    - `estado` sigue la máquina de estados definida en EstadoComunicacion.
    - `lote_id` es None para envíos individuales, UUID para envíos masivos.
    - `aprobado_at` solo se setea cuando el tenant requiere aprobación y el
      COORDINADOR/ADMIN aprueba el lote.
    """

    __tablename__ = "comunicacion"

    enviado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    materia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    # Cifrado AES-256-GCM en app-level — TEXT en BD
    destinatario: Mapped[str] = mapped_column(Text, nullable=False)
    asunto: Mapped[str] = mapped_column(String(500), nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoComunicacion] = mapped_column(
        Enum(EstadoComunicacion, name="estadocomunicacion"),
        nullable=False,
        default=EstadoComunicacion.Pendiente,
        index=True,
    )
    # None para envíos individuales; UUID compartido para lotes masivos
    lote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    enviado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    aprobado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        # ix_comunicacion_tenant_id ya creado por TenantMixin (index=True)
        # ix_comunicacion_estado creado por index=True arriba
        Index("ix_comunicacion_tenant_estado", "tenant_id", "estado"),
        Index("ix_comunicacion_tenant_lote", "tenant_id", "lote_id"),
    )
