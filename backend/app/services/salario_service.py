"""Servicio de grilla salarial — SalarioBase y SalarioPlus (C-18).

Responsabilidades:
- create_base(): validar solapamiento de vigencia antes de persistir → 409 si hay solapamiento.
- create_plus(): persistir sin validación de solapamiento (claves distintas pueden coexistir).
- list_grilla(): retornar base + plus del tenant.
- update_base(), update_plus(): actualizar campos permitidos.

NO accede directamente a la DB — siempre vía repositorios.
Identidad (tenant_id) SIEMPRE viene del caller (JWT verificado).
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status

from app.repositories.liquidacion_repository import SalarioBaseRepository, SalarioPlusRepository
from app.schemas.liquidacion import (
    GrillaSalarialResponse,
    SalarioBaseCreate,
    SalarioBaseResponse,
    SalarioBaseUpdate,
    SalarioPlusCreate,
    SalarioPlusResponse,
    SalarioPlusUpdate,
)


class SalarioService:
    def __init__(
        self,
        base_repo: SalarioBaseRepository,
        plus_repo: SalarioPlusRepository,
    ) -> None:
        self._base_repo = base_repo
        self._plus_repo = plus_repo

    # ── SalarioBase ───────────────────────────────────────────────────────────

    async def create_base(
        self, tenant_id: uuid.UUID, data: SalarioBaseCreate
    ) -> SalarioBaseResponse:
        """Crea un SalarioBase. Rechaza con 409 si hay solapamiento de vigencia para el rol."""
        solapa = await self._base_repo.check_solapamiento(
            tenant_id, data.rol, data.desde, data.hasta
        )
        if solapa:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un SalarioBase vigente para rol '{data.rol}' que solapa con el rango indicado",
            )
        obj = await self._base_repo.create(tenant_id, data.model_dump())
        return SalarioBaseResponse.model_validate(obj)

    async def update_base(
        self, tenant_id: uuid.UUID, salario_id: uuid.UUID, data: SalarioBaseUpdate
    ) -> SalarioBaseResponse:
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        obj = await self._base_repo.update(salario_id, tenant_id, update_data)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SalarioBase no encontrado")
        return SalarioBaseResponse.model_validate(obj)

    # ── SalarioPlus ───────────────────────────────────────────────────────────

    async def create_plus(
        self, tenant_id: uuid.UUID, data: SalarioPlusCreate
    ) -> SalarioPlusResponse:
        """Crea un SalarioPlus. No hay validación de solapamiento — claves distintas coexisten."""
        obj = await self._plus_repo.create(tenant_id, data.model_dump())
        return SalarioPlusResponse.model_validate(obj)

    async def update_plus(
        self, tenant_id: uuid.UUID, plus_id: uuid.UUID, data: SalarioPlusUpdate
    ) -> SalarioPlusResponse:
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        obj = await self._plus_repo.update(plus_id, tenant_id, update_data)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SalarioPlus no encontrado")
        return SalarioPlusResponse.model_validate(obj)

    # ── Grilla ────────────────────────────────────────────────────────────────

    async def list_grilla(self, tenant_id: uuid.UUID) -> GrillaSalarialResponse:
        base = await self._base_repo.list_by_tenant(tenant_id)
        plus = await self._plus_repo.list_by_tenant(tenant_id)
        return GrillaSalarialResponse(
            base=[SalarioBaseResponse.model_validate(b) for b in base],
            plus=[SalarioPlusResponse.model_validate(p) for p in plus],
        )
