"""Repositorio para el módulo de tareas internas (C-16).

Todas las queries incluyen filtro tenant_id por defecto — omitirlo es un bug.
Sin lógica de negocio: eso vive en TareaService.

Clases:
- TareaRepository: CRUD de Tarea con paginación para admin.
- ComentarioTareaRepository: append-only de ComentarioTarea.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tarea import ComentarioTarea, EstadoTarea, Tarea
from app.schemas.tarea import TareaCreate


class TareaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── create ────────────────────────────────────────────────────────────────

    async def create(
        self,
        tenant_id: uuid.UUID,
        asignado_por: uuid.UUID,
        data: TareaCreate,
    ) -> Tarea:
        """Persiste una tarea nueva con estado inicial pendiente."""
        tarea = Tarea(
            tenant_id=tenant_id,
            asignado_por=asignado_por,
            asignado_a=data.asignado_a,
            descripcion=data.descripcion,
            materia_id=data.materia_id,
            contexto_id=data.contexto_id,
            estado=EstadoTarea.pendiente,
        )
        self.session.add(tarea)
        await self.session.flush()
        await self.session.refresh(tarea)
        return tarea

    # ── get_by_id ─────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        tenant_id: uuid.UUID,
        tarea_id: uuid.UUID,
    ) -> Optional[Tarea]:
        """Obtiene una tarea por ID dentro del tenant. None si no existe o soft-deleted."""
        q = select(Tarea).where(
            Tarea.id == tarea_id,
            Tarea.tenant_id == tenant_id,
            Tarea.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    # ── list_mis_tareas ───────────────────────────────────────────────────────

    async def list_mis_tareas(
        self,
        tenant_id: uuid.UUID,
        asignado_a: uuid.UUID,
        estado: Optional[EstadoTarea] = None,
    ) -> list[Tarea]:
        """Lista las tareas asignadas al usuario, opcionalmente filtradas por estado."""
        conditions = [
            Tarea.tenant_id == tenant_id,
            Tarea.asignado_a == asignado_a,
            Tarea.deleted_at.is_(None),
        ]
        if estado is not None:
            conditions.append(Tarea.estado == estado)

        q = (
            select(Tarea)
            .where(and_(*conditions))
            .order_by(Tarea.created_at.desc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    # ── list_all ──────────────────────────────────────────────────────────────

    async def list_all(
        self,
        tenant_id: uuid.UUID,
        filters: dict,
        page: int,
        size: int,
    ) -> tuple[list[Tarea], int]:
        """Lista todas las tareas del tenant con filtros y paginación offset.

        filters puede contener: estado, asignado_a, asignado_por, materia_id.
        Retorna (items, total).
        """
        conditions = [
            Tarea.tenant_id == tenant_id,
            Tarea.deleted_at.is_(None),
        ]

        if filters.get("estado"):
            conditions.append(Tarea.estado == filters["estado"])
        if filters.get("asignado_a"):
            conditions.append(Tarea.asignado_a == filters["asignado_a"])
        if filters.get("asignado_por"):
            conditions.append(Tarea.asignado_por == filters["asignado_por"])
        if filters.get("materia_id"):
            conditions.append(Tarea.materia_id == filters["materia_id"])

        where_clause = and_(*conditions)

        count_q = select(func.count()).select_from(Tarea).where(where_clause)
        count_result = await self.session.execute(count_q)
        total = count_result.scalar_one()

        offset = (page - 1) * size
        items_q = (
            select(Tarea)
            .where(where_clause)
            .order_by(Tarea.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        items_result = await self.session.execute(items_q)
        items = list(items_result.scalars().all())

        return items, total

    # ── update_estado ─────────────────────────────────────────────────────────

    async def update_estado(
        self,
        tenant_id: uuid.UUID,
        tarea_id: uuid.UUID,
        nuevo_estado: EstadoTarea,
    ) -> Optional[Tarea]:
        """Actualiza el estado de una tarea. Retorna None si no existe."""
        q = (
            update(Tarea)
            .where(
                Tarea.id == tarea_id,
                Tarea.tenant_id == tenant_id,
                Tarea.deleted_at.is_(None),
            )
            .values(
                estado=nuevo_estado,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(Tarea)
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()


class ComentarioTareaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── create ────────────────────────────────────────────────────────────────

    async def create(
        self,
        tenant_id: uuid.UUID,
        tarea_id: uuid.UUID,
        autor_id: uuid.UUID,
        texto: str,
    ) -> ComentarioTarea:
        """Persiste un comentario append-only en la tarea."""
        comentario = ComentarioTarea(
            tenant_id=tenant_id,
            tarea_id=tarea_id,
            autor_id=autor_id,
            texto=texto,
            creado_at=datetime.now(timezone.utc),
        )
        self.session.add(comentario)
        await self.session.flush()
        await self.session.refresh(comentario)
        return comentario

    # ── list_comentarios ──────────────────────────────────────────────────────

    async def list_comentarios(
        self,
        tenant_id: uuid.UUID,
        tarea_id: uuid.UUID,
    ) -> list[ComentarioTarea]:
        """Lista los comentarios de una tarea ordenados cronológicamente."""
        q = (
            select(ComentarioTarea)
            .where(
                ComentarioTarea.tarea_id == tarea_id,
                ComentarioTarea.tenant_id == tenant_id,
            )
            .order_by(ComentarioTarea.creado_at.asc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())
