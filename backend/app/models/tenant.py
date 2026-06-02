from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean
from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin

class Tenant(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Root entity representing an institution.
    """
    __tablename__ = "tenant"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
