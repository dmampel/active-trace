"""Repositorio de asignaciones contextuales.

Reglas:
- Toda query filtra por tenant_id por defecto (row-level isolation).
- Soft delete via deleted_at — nunca hard delete.
- estado_vigencia NO se almacena — se deriva en derive_estado_vigencia().
- No lógica de negocio: eso pertenece al Service.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asignacion import Asignacion


class AsignacionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def derive_estado_vigencia(asig: Asignacion) -> str:
        """Deriva el estado de vigencia de una asignación.

        Vigente: desde <= hoy AND (hasta IS NULL OR hoy <= hasta)
        Vencida: hasta < hoy
        """
        today = date.today()
        if asig.desde > today:
            return "Futura"
        if asig.hasta is not None and asig.hasta < today:
            return "Vencida"
        return "Vigente"

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Asignacion:
        asig = Asignacion(id=uuid.uuid4(), tenant_id=tenant_id, **data)
        self.session.add(asig)
        await self.session.commit()
        await self.session.refresh(asig)
        return asig

    async def get_by_id(self, asig_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Asignacion]:
        q = select(Asignacion).where(
            Asignacion.id == asig_id,
            Asignacion.tenant_id == tenant_id,
            Asignacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        rol: Optional[str] = None,
        vigente_only: bool = False,
    ) -> list[Asignacion]:
        """Lista asignaciones con filtros opcionales, siempre acotadas a tenant."""
        conditions = [
            Asignacion.tenant_id == tenant_id,
            Asignacion.deleted_at.is_(None),
        ]
        if usuario_id is not None:
            conditions.append(Asignacion.usuario_id == usuario_id)
        if materia_id is not None:
            conditions.append(Asignacion.materia_id == materia_id)
        if cohorte_id is not None:
            conditions.append(Asignacion.cohorte_id == cohorte_id)
        if rol is not None:
            conditions.append(Asignacion.rol == rol)
        if vigente_only:
            today = date.today()
            conditions.append(Asignacion.desde <= today)
            conditions.append(or_(Asignacion.hasta.is_(None), Asignacion.hasta >= today))

        q = select(Asignacion).where(*conditions)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def list_vigentes(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> list[Asignacion]:
        """Alias conveniente: asignaciones vigentes de un tenant (opcionalmente por usuario)."""
        return await self.list(
            tenant_id,
            usuario_id=user_id,
            vigente_only=True,
        )

    async def update(
        self, asig_id: uuid.UUID, tenant_id: uuid.UUID, data: dict
    ) -> Optional[Asignacion]:
        asig = await self.get_by_id(asig_id, tenant_id)
        if not asig:
            return None
        for k, v in data.items():
            setattr(asig, k, v)
        await self.session.commit()
        await self.session.refresh(asig)
        return asig

    async def soft_delete(self, asig_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        asig = await self.get_by_id(asig_id, tenant_id)
        if not asig:
            return False
        asig.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True
