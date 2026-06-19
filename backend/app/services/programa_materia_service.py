"""Servicio para programas de materia (C-17).

Responsabilidades:
- Orquestar CRUD de ProgramaMateria delegando a ProgramaMateriaRepository.
- Convertir IntegrityError del repositorio en HTTPException(409).
- Lanzar HTTPException(404) cuando el recurso no existe.
- Sin acceso directo a DB — siempre vía repositorios.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models.programa_materia import ProgramaMateria
from app.repositories.programa_materia_repository import ProgramaMateriaRepository
from app.schemas.programa_materia import (
    ProgramaMateriaCreate,
    ProgramaMateriaOut,
    ProgramaMateriaUpdate,
)


class ProgramaMateriaService:
    def __init__(self, repo: ProgramaMateriaRepository) -> None:
        self.repo = repo

    # ── crear ─────────────────────────────────────────────────────────────────

    async def crear(
        self,
        tenant_id: uuid.UUID,
        data: ProgramaMateriaCreate,
    ) -> ProgramaMateriaOut:
        """Crea un programa de materia. 409 si ya existe para el mismo contexto."""
        try:
            programa = await self.repo.create(tenant_id, data)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un programa para este contexto académico (materia, carrera, cohorte)",
            )
        return _to_out(programa)

    # ── get_by_id ─────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        tenant_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> ProgramaMateriaOut:
        """Obtiene un programa por ID. 404 si no existe."""
        programa = await self.repo.get_by_id(tenant_id, programa_id)
        if programa is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Programa de materia no encontrado",
            )
        return _to_out(programa)

    # ── get_by_context ────────────────────────────────────────────────────────

    async def get_by_context(
        self,
        tenant_id: uuid.UUID,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> Optional[ProgramaMateriaOut]:
        """Obtiene el programa activo para un contexto académico. None si no existe."""
        programa = await self.repo.get_by_context(
            tenant_id, materia_id, carrera_id, cohorte_id
        )
        return _to_out(programa) if programa else None

    # ── actualizar ────────────────────────────────────────────────────────────

    async def actualizar(
        self,
        tenant_id: uuid.UUID,
        programa_id: uuid.UUID,
        data: ProgramaMateriaUpdate,
    ) -> ProgramaMateriaOut:
        """Actualiza un programa. 404 si no existe."""
        programa = await self.repo.update(tenant_id, programa_id, data)
        if programa is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Programa de materia no encontrado",
            )
        return _to_out(programa)

    # ── eliminar ──────────────────────────────────────────────────────────────

    async def eliminar(
        self,
        tenant_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> None:
        """Soft-delete un programa. 404 si no existe."""
        deleted = await self.repo.soft_delete(tenant_id, programa_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Programa de materia no encontrado",
            )


# ── Helper ────────────────────────────────────────────────────────────────────


def _to_out(p: ProgramaMateria) -> ProgramaMateriaOut:
    return ProgramaMateriaOut(
        id=p.id,
        tenant_id=p.tenant_id,
        materia_id=p.materia_id,
        carrera_id=p.carrera_id,
        cohorte_id=p.cohorte_id,
        titulo=p.titulo,
        referencia_archivo=p.referencia_archivo,
        cargado_at=p.cargado_at,
    )
