"""Repositorio para FechaAcademica (C-14 / C-17).

Todas las queries incluyen filtro tenant_id por defecto — omitirlo es un bug.
Sin lógica de negocio: eso vive en FechaAcademicaService.

C-17 agrega:
- Filtro `periodo` en list().
- Manejo de IntegrityError en create() y update() (unicidad por contexto).
- Firma canónica get_by_id(tenant_id, fecha_id).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluacion import FechaAcademica, TipoFechaAcademica


class FechaAcademicaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── create ────────────────────────────────────────────────────────────────

    async def create(self, fecha: FechaAcademica) -> FechaAcademica:
        """Persiste una fecha académica recién construida.

        Lanza IntegrityError si viola el UniqueConstraint de contexto.
        """
        self.session.add(fecha)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise
        await self.session.refresh(fecha)
        return fecha

    # ── get_by_id ─────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        tenant_id: uuid.UUID,
        fecha_id: uuid.UUID,
    ) -> Optional[FechaAcademica]:
        """Obtiene una fecha académica activa por ID dentro del tenant."""
        q = select(FechaAcademica).where(
            FechaAcademica.id == fecha_id,
            FechaAcademica.tenant_id == tenant_id,
            FechaAcademica.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    # ── list ──────────────────────────────────────────────────────────────────

    async def list(
        self,
        tenant_id: uuid.UUID,
        *,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        periodo: Optional[str] = None,
        tipo: Optional[TipoFechaAcademica] = None,
    ) -> list[FechaAcademica]:
        """Lista fechas académicas activas del tenant con filtros opcionales.

        Ordenadas por fecha ascendente.
        """
        conditions = [
            FechaAcademica.tenant_id == tenant_id,
            FechaAcademica.deleted_at.is_(None),
        ]
        if materia_id is not None:
            conditions.append(FechaAcademica.materia_id == materia_id)
        if cohorte_id is not None:
            conditions.append(FechaAcademica.cohorte_id == cohorte_id)
        if periodo is not None:
            conditions.append(FechaAcademica.periodo == periodo)
        if tipo is not None:
            conditions.append(FechaAcademica.tipo == tipo)

        q = (
            select(FechaAcademica)
            .where(and_(*conditions))
            .order_by(FechaAcademica.fecha.asc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    # ── list_by_tenant (alias de compatibilidad C-14) ─────────────────────────

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        tipo: Optional[TipoFechaAcademica] = None,
    ) -> list[FechaAcademica]:
        """Alias de list() sin filtro de periodo — mantiene compatibilidad C-14."""
        return await self.list(
            tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            tipo=tipo,
        )

    # ── update ────────────────────────────────────────────────────────────────

    async def update(
        self,
        fecha_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        tipo: Optional[TipoFechaAcademica] = None,
        numero: Optional[int] = None,
        periodo: Optional[str] = None,
        fecha: Optional[str] = None,
        titulo: Optional[str] = None,
    ) -> Optional[FechaAcademica]:
        """Actualiza campos de una fecha académica.

        Lanza IntegrityError si la actualización viola el UniqueConstraint.
        Retorna None si no existe.
        """
        values: dict = {"updated_at": datetime.now(timezone.utc)}
        if tipo is not None:
            values["tipo"] = tipo
        if numero is not None:
            values["numero"] = numero
        if periodo is not None:
            values["periodo"] = periodo
        if fecha is not None:
            values["fecha"] = fecha
        if titulo is not None:
            values["titulo"] = titulo

        q = (
            update(FechaAcademica)
            .where(
                FechaAcademica.id == fecha_id,
                FechaAcademica.tenant_id == tenant_id,
                FechaAcademica.deleted_at.is_(None),
            )
            .values(**values)
            .returning(FechaAcademica)
        )
        try:
            result = await self.session.execute(q)
        except IntegrityError:
            await self.session.rollback()
            raise
        return result.scalar_one_or_none()

    # ── soft_delete ───────────────────────────────────────────────────────────

    async def soft_delete(
        self,
        fecha_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Soft-delete una fecha académica. Retorna True si existía."""
        q = (
            update(FechaAcademica)
            .where(
                FechaAcademica.id == fecha_id,
                FechaAcademica.tenant_id == tenant_id,
                FechaAcademica.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(q)
        return result.rowcount > 0
