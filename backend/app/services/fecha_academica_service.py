"""Servicio para fechas académicas (C-14 / C-17).

Responsabilidades:
- Orquestar CRUD de FechaAcademica delegando a FechaAcademicaRepository.
- Convertir IntegrityError del repositorio en HTTPException(409).
- Lanzar HTTPException(404) cuando el recurso no existe.
- Generar fragmento Markdown con fechas ordenadas para el LMS.
- Sin acceso directo a DB — siempre vía repositorios.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models.evaluacion import FechaAcademica, TipoFechaAcademica
from app.repositories.fecha_academica_repository import FechaAcademicaRepository
from app.schemas.fecha_academica import (
    FechaAcademicaCreate,
    FechaAcademicaRead,
    FechaAcademicaUpdate,
    LMSFragmentOut,
)


class FechaAcademicaService:
    def __init__(self, repo: FechaAcademicaRepository) -> None:
        self.repo = repo

    # ── crear ─────────────────────────────────────────────────────────────────

    async def crear(
        self,
        data: FechaAcademicaCreate,
        tenant_id: uuid.UUID,
    ) -> FechaAcademicaRead:
        """Crea una fecha académica. 409 si viola unicidad de contexto."""
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
        try:
            fecha = await self.repo.create(fecha)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una fecha académica para este contexto (materia, cohorte, tipo, número, período)",
            )
        return _to_read(fecha)

    # ── get_by_id ─────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        tenant_id: uuid.UUID,
        fecha_id: uuid.UUID,
    ) -> FechaAcademicaRead:
        """Obtiene una fecha académica por ID. 404 si no existe."""
        fecha = await self.repo.get_by_id(tenant_id, fecha_id)
        if fecha is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fecha académica no encontrada",
            )
        return _to_read(fecha)

    # ── listar ────────────────────────────────────────────────────────────────

    async def listar(
        self,
        tenant_id: uuid.UUID,
        *,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        periodo: Optional[str] = None,
        tipo: Optional[TipoFechaAcademica] = None,
    ) -> list[FechaAcademicaRead]:
        """Lista fechas académicas del tenant con filtros opcionales."""
        items = await self.repo.list(
            tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            periodo=periodo,
            tipo=tipo,
        )
        return [_to_read(f) for f in items]

    # ── actualizar ────────────────────────────────────────────────────────────

    async def actualizar(
        self,
        fecha_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: FechaAcademicaUpdate,
    ) -> FechaAcademicaRead:
        """Actualiza campos de una fecha académica. 404 si no existe, 409 si viola unicidad."""
        try:
            fecha = await self.repo.update(
                fecha_id,
                tenant_id,
                tipo=data.tipo,
                numero=data.numero,
                periodo=data.periodo,
                fecha=data.fecha,
                titulo=data.titulo,
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La actualización viola la unicidad de contexto (materia, cohorte, tipo, número, período)",
            )
        if fecha is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fecha académica no encontrada",
            )
        return _to_read(fecha)

    # ── eliminar ──────────────────────────────────────────────────────────────

    async def eliminar(
        self,
        fecha_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        """Soft-delete una fecha académica. 404 si no existe."""
        deleted = await self.repo.soft_delete(fecha_id, tenant_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fecha académica no encontrada",
            )

    # ── generar_fragmento_lms ─────────────────────────────────────────────────

    async def generar_fragmento_lms(
        self,
        tenant_id: uuid.UUID,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        periodo: str,
    ) -> LMSFragmentOut:
        """Genera un fragmento Markdown con las fechas del período, ordenadas cronológicamente.

        Ejemplo de output:
        ## Fechas Académicas — 2026-1

        - **2026-04-15** — Parcial 1: Primer Parcial
        - **2026-05-20** — TP 1: Trabajo Práctico 1
        """
        fechas = await self.repo.list(
            tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            periodo=periodo,
        )

        if not fechas:
            fragmento = f"## Fechas Académicas — {periodo}\n\n_Sin fechas registradas para este período._"
        else:
            lineas = [f"## Fechas Académicas — {periodo}", ""]
            for f in fechas:
                lineas.append(f"- **{f.fecha}** — {f.tipo.value} {f.numero}: {f.titulo}")
            fragmento = "\n".join(lineas)

        return LMSFragmentOut(fragmento=fragmento)


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
