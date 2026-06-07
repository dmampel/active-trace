import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.estructura import Carrera, Cohorte, EstadoEntidad, InstanciaDictado, Materia


class CarreraRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Carrera:
        obj = Carrera(id=uuid.uuid4(), tenant_id=tenant_id, estado=EstadoEntidad.activa, **data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Carrera]:
        q = select(Carrera).where(Carrera.id == id, Carrera.tenant_id == tenant_id, Carrera.deleted_at.is_(None))
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_active(self, tenant_id: uuid.UUID) -> list[Carrera]:
        q = select(Carrera).where(Carrera.tenant_id == tenant_id, Carrera.deleted_at.is_(None))
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> Optional[Carrera]:
        obj = await self.get_by_id(id, tenant_id)
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        obj = await self.get_by_id(id, tenant_id)
        if not obj:
            return False
        q = (
            update(Carrera)
            .where(Carrera.id == id, Carrera.tenant_id == tenant_id)
            .values(deleted_at=func.now())
        )
        await self.session.execute(q)
        await self.session.commit()
        return True


class CohorteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Cohorte:
        obj = Cohorte(id=uuid.uuid4(), tenant_id=tenant_id, estado=EstadoEntidad.activa, **data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Cohorte]:
        q = select(Cohorte).where(Cohorte.id == id, Cohorte.tenant_id == tenant_id, Cohorte.deleted_at.is_(None))
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_active(self, tenant_id: uuid.UUID, carrera_id: Optional[uuid.UUID] = None) -> list[Cohorte]:
        q = select(Cohorte).where(Cohorte.tenant_id == tenant_id, Cohorte.deleted_at.is_(None))
        if carrera_id:
            q = q.where(Cohorte.carrera_id == carrera_id)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> Optional[Cohorte]:
        obj = await self.get_by_id(id, tenant_id)
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        obj = await self.get_by_id(id, tenant_id)
        if not obj:
            return False
        q = (
            update(Cohorte)
            .where(Cohorte.id == id, Cohorte.tenant_id == tenant_id)
            .values(deleted_at=func.now())
        )
        await self.session.execute(q)
        await self.session.commit()
        return True


class MateriaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Materia:
        obj = Materia(id=uuid.uuid4(), tenant_id=tenant_id, estado=EstadoEntidad.activa, **data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Materia]:
        q = select(Materia).where(Materia.id == id, Materia.tenant_id == tenant_id, Materia.deleted_at.is_(None))
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_active(self, tenant_id: uuid.UUID) -> list[Materia]:
        q = select(Materia).where(Materia.tenant_id == tenant_id, Materia.deleted_at.is_(None))
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> Optional[Materia]:
        obj = await self.get_by_id(id, tenant_id)
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        obj = await self.get_by_id(id, tenant_id)
        if not obj:
            return False
        q = (
            update(Materia)
            .where(Materia.id == id, Materia.tenant_id == tenant_id)
            .values(deleted_at=func.now())
        )
        await self.session.execute(q)
        await self.session.commit()
        return True


class InstanciaDictadoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, data: dict) -> InstanciaDictado:
        obj = InstanciaDictado(id=uuid.uuid4(), tenant_id=tenant_id, estado=EstadoEntidad.activa, **data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[InstanciaDictado]:
        q = select(InstanciaDictado).where(
            InstanciaDictado.id == id,
            InstanciaDictado.tenant_id == tenant_id,
            InstanciaDictado.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_active(
        self,
        tenant_id: uuid.UUID,
        cohorte_id: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
    ) -> list[InstanciaDictado]:
        q = select(InstanciaDictado).where(
            InstanciaDictado.tenant_id == tenant_id,
            InstanciaDictado.deleted_at.is_(None),
        )
        if cohorte_id:
            q = q.where(InstanciaDictado.cohorte_id == cohorte_id)
        if materia_id:
            q = q.where(InstanciaDictado.materia_id == materia_id)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> Optional[InstanciaDictado]:
        obj = await self.get_by_id(id, tenant_id)
        if not obj:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        obj = await self.get_by_id(id, tenant_id)
        if not obj:
            return False
        q = (
            update(InstanciaDictado)
            .where(InstanciaDictado.id == id, InstanciaDictado.tenant_id == tenant_id)
            .values(deleted_at=func.now())
        )
        await self.session.execute(q)
        await self.session.commit()
        return True
