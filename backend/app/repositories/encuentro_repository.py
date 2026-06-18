"""Repositorios para SlotEncuentro e InstanciaEncuentro (C-13).

Todas las queries incluyen filtro tenant_id por defecto — omitirlo es un bug.
Sin lógica de negocio: eso vive en EncuentrosService.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encuentro import EstadoInstanciaEncuentro, InstanciaEncuentro, SlotEncuentro


class SlotEncuentroRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, slot: SlotEncuentro) -> SlotEncuentro:
        """Persiste un slot recién construido."""
        self.session.add(slot)
        await self.session.flush()
        await self.session.refresh(slot)
        return slot

    async def get_by_id(
        self,
        slot_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[SlotEncuentro]:
        """Obtiene un slot por ID dentro del tenant, excluyendo soft-deleted."""
        q = select(SlotEncuentro).where(
            SlotEncuentro.id == slot_id,
            SlotEncuentro.tenant_id == tenant_id,
            SlotEncuentro.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_by_asignacion(
        self,
        asignacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[SlotEncuentro]:
        """Lista slots de una asignación específica dentro del tenant."""
        q = select(SlotEncuentro).where(
            SlotEncuentro.asignacion_id == asignacion_id,
            SlotEncuentro.tenant_id == tenant_id,
            SlotEncuentro.deleted_at.is_(None),
        ).order_by(SlotEncuentro.created_at.asc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def list_all_tenant(
        self,
        tenant_id: uuid.UUID,
    ) -> list[SlotEncuentro]:
        """Lista todos los slots del tenant (vista COORDINADOR/ADMIN)."""
        q = select(SlotEncuentro).where(
            SlotEncuentro.tenant_id == tenant_id,
            SlotEncuentro.deleted_at.is_(None),
        ).order_by(SlotEncuentro.created_at.desc())
        result = await self.session.execute(q)
        return list(result.scalars().all())


class InstanciaEncuentroRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(
        self,
        instancias: list[InstanciaEncuentro],
    ) -> list[InstanciaEncuentro]:
        """Persiste varias instancias de una vez (generación recurrente)."""
        for instancia in instancias:
            self.session.add(instancia)
        await self.session.flush()
        for instancia in instancias:
            await self.session.refresh(instancia)
        return instancias

    async def get_by_id(
        self,
        instancia_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[InstanciaEncuentro]:
        """Obtiene una instancia por ID dentro del tenant, excluyendo soft-deleted."""
        q = select(InstanciaEncuentro).where(
            InstanciaEncuentro.id == instancia_id,
            InstanciaEncuentro.tenant_id == tenant_id,
            InstanciaEncuentro.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def update(
        self,
        instancia_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        estado: Optional[EstadoInstanciaEncuentro] = None,
        meet_url: Optional[str] = None,
        video_url: Optional[str] = None,
        comentario: Optional[str] = None,
    ) -> Optional[InstanciaEncuentro]:
        """Actualiza solo los campos provistos de una instancia (RN-14)."""
        values: dict = {}
        if estado is not None:
            values["estado"] = estado
        if meet_url is not None:
            values["meet_url"] = meet_url
        if video_url is not None:
            values["video_url"] = video_url
        if comentario is not None:
            values["comentario"] = comentario

        if not values:
            # Nada que actualizar — devolver la instancia sin tocarla
            return await self.get_by_id(instancia_id, tenant_id)

        q = (
            update(InstanciaEncuentro)
            .where(
                InstanciaEncuentro.id == instancia_id,
                InstanciaEncuentro.tenant_id == tenant_id,
                InstanciaEncuentro.deleted_at.is_(None),
            )
            .values(**values)
            .returning(InstanciaEncuentro)
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_by_slot(
        self,
        slot_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[InstanciaEncuentro]:
        """Lista todas las instancias de un slot dentro del tenant."""
        q = select(InstanciaEncuentro).where(
            InstanciaEncuentro.slot_id == slot_id,
            InstanciaEncuentro.tenant_id == tenant_id,
            InstanciaEncuentro.deleted_at.is_(None),
        ).order_by(InstanciaEncuentro.fecha.asc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def list_all_tenant(
        self,
        tenant_id: uuid.UUID,
    ) -> list[InstanciaEncuentro]:
        """Lista todas las instancias del tenant (vista COORDINADOR/ADMIN)."""
        q = select(InstanciaEncuentro).where(
            InstanciaEncuentro.tenant_id == tenant_id,
            InstanciaEncuentro.deleted_at.is_(None),
        ).order_by(InstanciaEncuentro.fecha.asc())
        result = await self.session.execute(q)
        return list(result.scalars().all())
