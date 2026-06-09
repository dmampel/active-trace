import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin
from app.models.estructura import EstadoEntidad


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)

    # 2FA TOTP — almacenados cifrados (AES-256). NULL hasta enrolamiento.
    totp_secret_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    totp_pending_secret_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Perfil de persona (C-07) ──────────────────────────────────────────────
    nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    apellidos: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # PII cifrada (AES-256-GCM) — solo Service descifra/cifra, nunca Repository ni Model
    dni_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cuil_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cbu_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    alias_cbu_enc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    banco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    regional: Mapped[str | None] = mapped_column(String(100), nullable=True)
    legajo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    legajo_profesional: Mapped[str | None] = mapped_column(String(50), nullable=True)
    facturador: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    estado: Mapped[EstadoEntidad] = mapped_column(
        Enum(EstadoEntidad, name="estadoentidad"),
        nullable=False,
        default=EstadoEntidad.activa,
    )

    __table_args__ = (
        Index("ix_user_tenant_email", "tenant_id", "email", unique=True),
    )


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refresh_token"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "password_reset_token"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
