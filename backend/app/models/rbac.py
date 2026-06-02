import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Rol(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "rol"

    nombre: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Permiso(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "permiso"

    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)


class RolPermiso(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "rol_permiso"

    rol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rol.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permiso_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permiso.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (UniqueConstraint("rol_id", "permiso_id", name="uq_rol_permiso"),)


class UserRol(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "user_rol"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rol.id", ondelete="CASCADE"), nullable=False, index=True
    )
    desde: Mapped[date] = mapped_column(Date, nullable=False)
    hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
