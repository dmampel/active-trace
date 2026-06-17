"""Repositorio para UmbralMateria (C-10).

Responsabilidades:
- Todas las queries son tenant-scoped por defecto.
- Upsert idempotente por (tenant, asignacion, materia): sin duplicados.
- Sin lógica de negocio (el Service resuelve el umbral vigente y el defecto).
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import UmbralMateria


class UmbralRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_asignacion_materia(
        self,
        tenant_id: uuid.UUID,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
    ) -> Optional[UmbralMateria]:
        """Obtiene el umbral para (tenant, asignacion, materia) o None si no existe."""
        q = select(UmbralMateria).where(
            UmbralMateria.tenant_id == tenant_id,
            UmbralMateria.asignacion_id == asignacion_id,
            UmbralMateria.materia_id == materia_id,
            UmbralMateria.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        umbral: UmbralMateria,
        tenant_id: uuid.UUID,
    ) -> UmbralMateria:
        """Crea o actualiza el umbral para (tenant, asignacion, materia).

        Garantiza unicidad: si ya existe un umbral para la misma combinación,
        actualiza sus campos en lugar de crear un duplicado.
        """
        existing = await self.get_by_asignacion_materia(
            tenant_id=tenant_id,
            asignacion_id=umbral.asignacion_id,
            materia_id=umbral.materia_id,
        )
        if existing is not None:
            existing.umbral_pct = umbral.umbral_pct
            existing.valores_aprobatorios = umbral.valores_aprobatorios
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        umbral.tenant_id = tenant_id
        self.session.add(umbral)
        await self.session.commit()
        await self.session.refresh(umbral)
        return umbral
