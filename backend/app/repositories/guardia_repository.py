"""Repositorio para Guardia (C-13).

Todas las queries incluyen filtro tenant_id por defecto — omitirlo es un bug.
Sin lógica de negocio: eso vive en GuardiaService.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardia import EstadoGuardia, Guardia


class GuardiaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, guardia: Guardia) -> Guardia:
        """Persiste una guardia recién construida."""
        self.session.add(guardia)
        await self.session.flush()
        await self.session.refresh(guardia)
        return guardia

    async def get_by_id(
        self,
        guardia_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[Guardia]:
        """Obtiene una guardia por ID dentro del tenant, excluyendo soft-deleted."""
        q = select(Guardia).where(
            Guardia.id == guardia_id,
            Guardia.tenant_id == tenant_id,
            Guardia.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_by_asignacion(
        self,
        asignacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        materia_id: Optional[uuid.UUID] = None,
        estado: Optional[EstadoGuardia] = None,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
    ) -> list[Guardia]:
        """Lista guardias de una asignación específica con filtros opcionales."""
        conditions = [
            Guardia.asignacion_id == asignacion_id,
            Guardia.tenant_id == tenant_id,
            Guardia.deleted_at.is_(None),
        ]
        if materia_id is not None:
            conditions.append(Guardia.materia_id == materia_id)
        if estado is not None:
            conditions.append(Guardia.estado == estado)
        if desde is not None:
            conditions.append(Guardia.dia >= desde)
        if hasta is not None:
            conditions.append(Guardia.dia <= hasta)

        q = select(Guardia).where(and_(*conditions)).order_by(Guardia.dia.asc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def list_all_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        materia_id: Optional[uuid.UUID] = None,
        estado: Optional[EstadoGuardia] = None,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
    ) -> list[Guardia]:
        """Lista todas las guardias del tenant con filtros opcionales (COORDINADOR/ADMIN)."""
        conditions = [
            Guardia.tenant_id == tenant_id,
            Guardia.deleted_at.is_(None),
        ]
        if materia_id is not None:
            conditions.append(Guardia.materia_id == materia_id)
        if estado is not None:
            conditions.append(Guardia.estado == estado)
        if desde is not None:
            conditions.append(Guardia.dia >= desde)
        if hasta is not None:
            conditions.append(Guardia.dia <= hasta)

        q = select(Guardia).where(and_(*conditions)).order_by(Guardia.dia.asc())
        result = await self.session.execute(q)
        return list(result.scalars().all())
