"""Repositorio para Calificacion (C-10).

Responsabilidades:
- Todas las queries son tenant-scoped por defecto.
- Sin lógica de negocio (ni derivación de aprobado, ni parsing, ni auditoría).
- Soft delete: las queries de listado excluyen filas con deleted_at no nulo.
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import Calificacion


class CalificacionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def crear(self, calificacion: Calificacion) -> Calificacion:
        """Persiste una calificación y retorna la instancia con id asignado."""
        self.session.add(calificacion)
        await self.session.commit()
        await self.session.refresh(calificacion)
        return calificacion

    async def bulk_crear(self, calificaciones: list[Calificacion]) -> int:
        """Persiste una lista de calificaciones en un commit; retorna la cantidad persistida."""
        for cal in calificaciones:
            self.session.add(cal)
        await self.session.commit()
        return len(calificaciones)

    async def listar_por_materia(
        self,
        materia_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[Calificacion]:
        """Lista calificaciones de una materia para un tenant, excluyendo soft-deleted."""
        q = select(Calificacion).where(
            Calificacion.tenant_id == tenant_id,
            Calificacion.materia_id == materia_id,
            Calificacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def listar_por_entrada(
        self,
        entrada_padron_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[Calificacion]:
        """Lista calificaciones de un alumno (EntradaPadron), excluyendo soft-deleted."""
        q = select(Calificacion).where(
            Calificacion.tenant_id == tenant_id,
            Calificacion.entrada_padron_id == entrada_padron_id,
            Calificacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def listar_por_materia_y_actividades(
        self,
        materia_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actividades: list[str],
    ) -> list[Calificacion]:
        """Lista calificaciones de una materia filtrando por actividades seleccionadas."""
        q = select(Calificacion).where(
            Calificacion.tenant_id == tenant_id,
            Calificacion.materia_id == materia_id,
            Calificacion.actividad.in_(actividades),
            Calificacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_entrada_y_actividad(
        self,
        entrada_padron_id: uuid.UUID,
        actividad: str,
        tenant_id: uuid.UUID,
    ) -> Optional[Calificacion]:
        """Obtiene la calificación de un alumno en una actividad específica."""
        q = select(Calificacion).where(
            Calificacion.tenant_id == tenant_id,
            Calificacion.entrada_padron_id == entrada_padron_id,
            Calificacion.actividad == actividad,
            Calificacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()
