"""Servicio de facturas de docentes monotributistas (C-18).

Responsabilidades:
- create(): verificar que usuario.facturador == True antes de persistir.
- update_estado(): solo Pendiente → Abonada; registra abonada_at.
- list_with_filters(): retornar facturas paginadas con filtros.

NO accede directamente a la DB — siempre vía repositorios.
Identidad (tenant_id) SIEMPRE viene del caller (JWT verificado).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.models.liquidacion import EstadoFactura
from app.repositories.liquidacion_repository import FacturaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.liquidacion import FacturaCreate, FacturaPatchRequest, FacturaResponse


class FacturaService:
    def __init__(
        self,
        factura_repo: FacturaRepository,
        usuario_repo: UsuarioRepository,
    ) -> None:
        self._repo = factura_repo
        self._usuario_repo = usuario_repo

    async def create(self, tenant_id: uuid.UUID, data: FacturaCreate) -> FacturaResponse:
        """Crea una factura. Verifica que el usuario sea facturante (facturador=True)."""
        usuario = await self._usuario_repo.get_by_id(data.usuario_id, tenant_id)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        if not usuario.facturador:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario no es facturante (facturador=false)",
            )

        now = datetime.now(timezone.utc)
        obj_data = data.model_dump()
        obj_data["estado"] = EstadoFactura.pendiente
        obj_data["cargada_at"] = now

        obj = await self._repo.create(tenant_id, obj_data)
        return FacturaResponse.model_validate(obj)

    async def update_estado(
        self,
        tenant_id: uuid.UUID,
        factura_id: uuid.UUID,
        data: FacturaPatchRequest,
    ) -> FacturaResponse:
        """Actualiza el estado de una factura. Solo Pendiente → Abonada."""
        factura = await self._repo.get_by_id(factura_id, tenant_id)
        if factura is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )
        if factura.estado != EstadoFactura.pendiente:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No se puede cambiar el estado desde '{factura.estado.value}'",
            )
        if data.estado != EstadoFactura.abonada:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Solo se permite transición Pendiente → Abonada",
            )

        obj = await self._repo.update_estado(factura_id, tenant_id, data.estado)
        return FacturaResponse.model_validate(obj)

    async def list_with_filters(
        self,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
        estado: Optional[EstadoFactura] = None,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
    ) -> list[FacturaResponse]:
        facturas = await self._repo.list_with_filters(tenant_id, usuario_id, estado, desde, hasta)
        return [FacturaResponse.model_validate(f) for f in facturas]
