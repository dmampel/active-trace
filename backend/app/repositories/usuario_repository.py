"""Repositorio de usuarios.

Reglas:
- Toda query filtra por tenant_id por defecto (row-level isolation).
- Soft delete via deleted_at — nunca hard delete.
- No cifra/descifra PII — eso es responsabilidad del Service.
- Unicidad (tenant_id, email) enforced por la DB; IntegrityError propagado al Service.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.user import User


class UsuarioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, data: dict) -> User:
        user = User(id=uuid.uuid4(), tenant_id=tenant_id, **data)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[User]:
        q = select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_active(self, tenant_id: uuid.UUID) -> list[User]:
        q = select(User).where(
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def update(self, user_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> Optional[User]:
        user = await self.get_by_id(user_id, tenant_id)
        if not user:
            return None
        for k, v in data.items():
            setattr(user, k, v)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def soft_delete(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        user = await self.get_by_id(user_id, tenant_id)
        if not user:
            return False
        user.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True
