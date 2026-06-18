"""Servicio para fechas académicas (C-14).

Responsabilidades:
- Orquestar CRUD de FechaAcademica delegando a FechaAcademicaRepository.
- Sin lógica de RBAC — eso vive en los routers.
- Sin acceso directo a DB — siempre vía repositorios.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status

from app.models.evaluacion import FechaAcademica, TipoFechaAcademica
from app.repositories.fecha_academica_repository import FechaAcademicaRepository
from app.schemas.fecha_academica import (
    FechaAcademicaCreate,
    FechaAcademicaRead,
    FechaAcademicaUpdate,
)


class FechaAcademicaService:
    def __init__(self, repo: FechaAcademicaRepository) -> None:
        self.repo = repo

    async def crear(
        self,
        data: FechaAcademicaCreate,
        tenant_id: uuid.UUID,
    ) -> FechaAcademicaRead:
        """Crea una fecha académica."""
        fecha = FechaAcademica(
            tenant_id=tenant_id,
            materia_id=data.materia_id,
            cohorte_id=data.cohorte_id,
            tipo=data.tipo,
            numero=data.numero,
            periodo=data.periodo,
            fecha=data.fecha,
            titulo=data.titulo,
        )
        fecha = await self.repo.create(fecha)
        return _to_read(fecha)

    async def listar(
        self,
        tenant_id: uuid.UUID,
        *,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        tipo: Optional[TipoFechaAcademica] = None,
    ) -> list[FechaAcademicaRead]:
        """Lista fechas académicas del tenant con filtros opcionales."""
        items = await self.repo.list_by_tenant(
            tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            tipo=tipo,
        )
        return [_to_read(f) for f in items]

    async def actualizar(
        self,
        fecha_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: FechaAcademicaUpdate,
    ) -> FechaAcademicaRead:
        """Actualiza campos de una fecha académica."""
        fecha = await self.repo.update(
            fecha_id,
            tenant_id,
            tipo=data.tipo,
            numero=data.numero,
            periodo=data.periodo,
            fecha=data.fecha,
            titulo=data.titulo,
        )
        if fecha is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fecha académica no encontrada",
            )
        return _to_read(fecha)

    async def eliminar(
        self,
        fecha_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        """Soft-delete una fecha académica."""
        deleted = await self.repo.soft_delete(fecha_id, tenant_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fecha académica no encontrada",
            )


# ── Helper ────────────────────────────────────────────────────────────────────


def _to_read(f: FechaAcademica) -> FechaAcademicaRead:
    return FechaAcademicaRead(
        id=f.id,
        tenant_id=f.tenant_id,
        materia_id=f.materia_id,
        cohorte_id=f.cohorte_id,
        tipo=f.tipo,
        numero=f.numero,
        periodo=f.periodo,
        fecha=f.fecha,
        titulo=f.titulo,
    )
