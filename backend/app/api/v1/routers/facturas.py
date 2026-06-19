"""Router de facturas de docentes monotributistas (C-18).

Endpoints:
    POST   /api/v1/facturas          → FacturaResponse  (201)  [liquidaciones:calcular]
    GET    /api/v1/facturas          → list[FacturaResponse] (200) [liquidaciones:ver]
    PATCH  /api/v1/facturas/{id}     → FacturaResponse  (200)  [liquidaciones:calcular]

Permisos (RBAC fail-closed):
    liquidaciones:calcular  → POST, PATCH
    liquidaciones:ver       → GET

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.models.liquidacion import EstadoFactura
from app.repositories.liquidacion_repository import FacturaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.liquidacion import FacturaCreate, FacturaPatchRequest, FacturaResponse
from app.services.factura_service import FacturaService

router = APIRouter(prefix="/api/v1/facturas", tags=["facturas"])


def _get_factura_service(db: AsyncSession = Depends(get_db)) -> FacturaService:
    return FacturaService(
        factura_repo=FacturaRepository(db),
        usuario_repo=UsuarioRepository(db),
    )


# ── POST /facturas ────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=FacturaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("liquidaciones:calcular"))],
)
async def create_factura(
    data: FacturaCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: FacturaService = Depends(_get_factura_service),
    db: AsyncSession = Depends(get_db),
):
    """Carga una factura de docente facturante. El docente debe tener facturador=True."""
    result = await svc.create(current_user.tenant_id, data)
    await db.commit()
    return result


# ── GET /facturas ─────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[FacturaResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("liquidaciones:ver"))],
)
async def list_facturas(
    usuario_id: Optional[uuid.UUID] = None,
    estado: Optional[EstadoFactura] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    svc: FacturaService = Depends(_get_factura_service),
):
    """Lista facturas del tenant con filtros opcionales."""
    return await svc.list_with_filters(
        current_user.tenant_id, usuario_id, estado, desde, hasta
    )


# ── PATCH /facturas/{id} ──────────────────────────────────────────────────────


@router.patch(
    "/{factura_id}",
    response_model=FacturaResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("liquidaciones:calcular"))],
)
async def update_factura(
    factura_id: uuid.UUID,
    data: FacturaPatchRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: FacturaService = Depends(_get_factura_service),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza el estado de una factura (Pendiente → Abonada)."""
    result = await svc.update_estado(current_user.tenant_id, factura_id, data)
    await db.commit()
    return result
