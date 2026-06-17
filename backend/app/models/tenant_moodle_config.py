"""Modelo SQLAlchemy para la configuración de Moodle por tenant.

TenantMoodleConfig: almacena la URL y token de Moodle Web Services para un tenant.
Ambos campos son PII/secretos y se almacenan cifrados con AES-256-GCM.

Invariante: un tenant tiene como máximo una configuración (UNIQUE en tenant_id).
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TenantMoodleConfig(Base, UUIDMixin, TimestampMixin):
    """Configuración de conexión a Moodle WS para un tenant específico."""

    __tablename__ = "tenant_moodle_config"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Ambos campos son secretos almacenados cifrados (AES-256-GCM).
    # El Service descifra antes de pasarlos al MoodleWSClient.
    moodle_url_enc: Mapped[str] = mapped_column(String(512), nullable=False)
    moodle_token_enc: Mapped[str] = mapped_column(String(512), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_moodle_config_tenant"),
    )
