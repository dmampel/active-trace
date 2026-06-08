import uuid
from datetime import date
from typing import List, Set

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permiso, Rol, RolPermiso, UserRol


class RbacRepository:
    @staticmethod
    def _get_active_roles_query(user_id: uuid.UUID, tenant_id: uuid.UUID):
        today = date.today()
        return (
            select(Rol)
            .join(UserRol, UserRol.rol_id == Rol.id)
            .where(
                UserRol.user_id == user_id,
                UserRol.tenant_id == tenant_id,
                UserRol.desde <= today,
                or_(UserRol.hasta == None, UserRol.hasta >= today),  # noqa: E711
            )
        )

    @staticmethod
    async def get_user_roles(session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> List[str]:
        stmt = RbacRepository._get_active_roles_query(user_id, tenant_id)
        result = await session.execute(stmt)
        roles = result.scalars().all()
        return [r.nombre for r in roles]

    @staticmethod
    async def get_effective_permissions(session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> Set[str]:
        today = date.today()
        stmt = (
            select(Permiso.nombre)
            .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
            .join(UserRol, UserRol.rol_id == RolPermiso.rol_id)
            .where(
                UserRol.user_id == user_id,
                UserRol.tenant_id == tenant_id,
                UserRol.desde <= today,
                or_(UserRol.hasta == None, UserRol.hasta >= today),  # noqa: E711
            )
        )
        result = await session.execute(stmt)
        perms = result.scalars().all()
        return set(perms)
