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
        """Resolución de permisos efectivos.

        Incluye:
        1. Permisos del rol global (user_rol) con vigencia activa.
        2. Permisos derivados de asignaciones contextuales (asignacion) vigentes.

        Una asignación vencida (hasta < hoy) o con soft_delete NO contribuye.
        """
        today = date.today()

        # ── Plano global: user_rol ─────────────────────────────────────────────
        stmt_global = (
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
        result_global = await session.execute(stmt_global)
        perms: Set[str] = set(result_global.scalars().all())

        # ── Plano contextual: asignacion ──────────────────────────────────────
        try:
            from sqlalchemy import cast, String
            from app.models.asignacion import Asignacion
            stmt_ctx = (
                select(Permiso.nombre)
                .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
                .join(Rol, Rol.id == RolPermiso.rol_id)
                .join(Asignacion, cast(Asignacion.rol, String) == Rol.nombre)
                .where(
                    Asignacion.usuario_id == user_id,
                    Asignacion.tenant_id == tenant_id,
                    Asignacion.deleted_at.is_(None),
                    Asignacion.desde <= today,
                    or_(Asignacion.hasta.is_(None), Asignacion.hasta >= today),
                )
            )
            result_ctx = await session.execute(stmt_ctx)
            perms.update(result_ctx.scalars().all())
        except Exception:
            # Si la tabla asignacion no existe todavía (migraciones no aplicadas),
            # continuamos sin permisos contextuales
            pass

        return perms
