"""Modelos de mensajería interna (C-20).

Completamente separados de ComunicacionDocente (C-12).
Hilo de dos participantes: autor inicial + destinatario.
Sin cola, sin adjuntos, sin grupos. Solo in-app.

Tablas:
- hilo_mensaje: conversación con asunto
- mensaje_interno: mensaje dentro del hilo
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class HiloMensaje(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Conversación interna entre dos usuarios del mismo tenant."""

    __tablename__ = "hilo_mensaje"

    asunto: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class MensajeInterno(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Mensaje individual dentro de un hilo interno."""

    __tablename__ = "mensaje_interno"

    hilo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hilo_mensaje.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destinatario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    leido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
