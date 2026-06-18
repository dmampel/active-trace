"""Router de guardias (C-13).

Endpoints:
    POST /api/v1/guardias         → GuardiaResponse (HTTP 201)
    GET  /api/v1/guardias         → list[GuardiaResponse]
    GET  /api/v1/guardias/export  → StreamingResponse (CSV)

Permisos (RBAC fail-closed):
    guardias:registrar → POST /
    guardias:consultar → GET /
    guardias:exportar  → GET /export

Identidad: SIEMPRE desde CurrentUser del JWT.
asignacion_id del TUTOR: proviene de un query param que identifica la asignación
activa del TUTOR. En registrar(), el service la toma de ese param — NUNCA del body.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.models.guardia import EstadoGuardia
from app.repositories.guardia_repository import GuardiaRepository
from app.schemas.guardia import GuardiaCreate, GuardiaFilter, GuardiaResponse
from app.services.guardia_service import GuardiaService

router = APIRouter(prefix="/api/v1/guardias", tags=["guardias"])


# ── Dependency factory ─────────────────────────────────────────────────────────


def _get_guardia_service(db: AsyncSession = Depends(get_db)) -> GuardiaService:
    repo = GuardiaRepository(db)
    return GuardiaService(repo=repo)


# ── POST / ─────────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=GuardiaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("guardias:registrar"))],
)
async def registrar_guardia(
    data: GuardiaCreate,
    asignacion_id: uuid.UUID = Query(
        ..., description="ID de la asignación activa del TUTOR"
    ),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GuardiaService = Depends(_get_guardia_service),
    db: AsyncSession = Depends(get_db),
):
    """Registra una guardia propia del TUTOR.

    asignacion_id proviene del query param — jamás del body.
    tenant_id se toma del JWT.
    """
    result = await svc.registrar(
        data,
        asignacion_id=asignacion_id,
        tenant_id=current_user.tenant_id,
    )
    await db.commit()
    return result


# ── GET / ──────────────────────────────────────────────────────────────────────


@router.get(
    "/",
    response_model=list[GuardiaResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("guardias:consultar"))],
)
async def listar_guardias(
    asignacion_id: Optional[uuid.UUID] = Query(
        default=None,
        description="Filtra por asignación (TUTOR pasa la suya; COORDINADOR omite para ver todas)",
    ),
    materia_id: Optional[uuid.UUID] = Query(default=None),
    estado: Optional[EstadoGuardia] = Query(default=None),
    desde: Optional[date] = Query(default=None),
    hasta: Optional[date] = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GuardiaService = Depends(_get_guardia_service),
):
    """Lista guardias.

    TUTOR: pasa su asignacion_id → solo sus guardias.
    COORDINADOR/ADMIN: omite asignacion_id → todas las del tenant.
    """
    filtros = GuardiaFilter(
        materia_id=materia_id,
        estado=estado,
        desde=desde,
        hasta=hasta,
    )
    return await svc.listar(
        tenant_id=current_user.tenant_id,
        asignacion_id=asignacion_id,
        filtros=filtros,
    )


# ── GET /export ────────────────────────────────────────────────────────────────


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("guardias:exportar"))],
)
async def exportar_guardias_csv(
    materia_id: Optional[uuid.UUID] = Query(default=None),
    estado: Optional[EstadoGuardia] = Query(default=None),
    desde: Optional[date] = Query(default=None),
    hasta: Optional[date] = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GuardiaService = Depends(_get_guardia_service),
):
    """Exporta guardias del tenant en CSV usando streaming (D4)."""
    filtros = GuardiaFilter(
        materia_id=materia_id,
        estado=estado,
        desde=desde,
        hasta=hasta,
    )
    generator = svc.exportar_csv(
        tenant_id=current_user.tenant_id,
        filtros=filtros,
    )
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=guardias.csv"},
    )
