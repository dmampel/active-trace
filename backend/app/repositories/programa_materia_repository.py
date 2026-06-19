"""Repositorio para el módulo de programas de materia (C-17).

Todas las queries incluyen filtro tenant_id por defecto — omitirlo es un bug.
Sin lógica de negocio: eso vive en ProgramaMateriaService.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.programa_materia import ProgramaMateria
from app.schemas.programa_materia import ProgramaMateriaCreate, ProgramaMateriaUpdate


class ProgramaMateriaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── create ────────────────────────────────────────────────────────────────

    async def create(
        self,
        tenant_id: uuid.UUID,
        data: ProgramaMateriaCreate,
    ) -> ProgramaMateria:
        """Persiste un programa de materia nuevo.

        Lanza IntegrityError si ya existe un programa para el mismo contexto
        (tenant_id, materia_id, carrera_id, cohorte_id).
        """
        programa = ProgramaMateria(
            tenant_id=tenant_id,
            materia_id=data.materia_id,
            carrera_id=data.carrera_id,
            cohorte_id=data.cohorte_id,
            titulo=data.titulo,
            referencia_archivo=data.referencia_archivo,
            cargado_at=datetime.now(timezone.utc) if data.referencia_archivo else None,
        )
        self.session.add(programa)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise
        await self.session.refresh(programa)
        return programa

    # ── get_by_id ─────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        tenant_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> Optional[ProgramaMateria]:
        """Obtiene un programa por ID dentro del tenant. None si no existe o soft-deleted."""
        q = select(ProgramaMateria).where(
            ProgramaMateria.id == programa_id,
            ProgramaMateria.tenant_id == tenant_id,
            ProgramaMateria.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    # ── get_by_context ────────────────────────────────────────────────────────

    async def get_by_context(
        self,
        tenant_id: uuid.UUID,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> Optional[ProgramaMateria]:
        """Obtiene el programa activo para un contexto académico específico."""
        q = select(ProgramaMateria).where(
            and_(
                ProgramaMateria.tenant_id == tenant_id,
                ProgramaMateria.materia_id == materia_id,
                ProgramaMateria.carrera_id == carrera_id,
                ProgramaMateria.cohorte_id == cohorte_id,
                ProgramaMateria.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    # ── update ────────────────────────────────────────────────────────────────

    async def update(
        self,
        tenant_id: uuid.UUID,
        programa_id: uuid.UUID,
        data: ProgramaMateriaUpdate,
    ) -> Optional[ProgramaMateria]:
        """Actualiza campos de un programa de materia. Retorna None si no existe."""
        values: dict = {"updated_at": datetime.now(timezone.utc)}
        if data.titulo is not None:
            values["titulo"] = data.titulo
        if data.referencia_archivo is not None:
            values["referencia_archivo"] = data.referencia_archivo
            values["cargado_at"] = datetime.now(timezone.utc)

        q = (
            update(ProgramaMateria)
            .where(
                ProgramaMateria.id == programa_id,
                ProgramaMateria.tenant_id == tenant_id,
                ProgramaMateria.deleted_at.is_(None),
            )
            .values(**values)
            .returning(ProgramaMateria)
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    # ── soft_delete ───────────────────────────────────────────────────────────

    async def soft_delete(
        self,
        tenant_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> bool:
        """Soft-delete un programa de materia. Retorna True si existía."""
        q = (
            update(ProgramaMateria)
            .where(
                ProgramaMateria.id == programa_id,
                ProgramaMateria.tenant_id == tenant_id,
                ProgramaMateria.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(q)
        return result.rowcount > 0
