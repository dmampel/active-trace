"""Router de fechas académicas (C-14).

Endpoints:
    POST   /api/v1/fechas-academicas            → FechaAcademicaRead (201)
    GET    /api/v1/fechas-academicas            → list[FechaAcademicaRead]
    PUT    /api/v1/fechas-academicas/{id}       → FechaAcademicaRead
    DELETE /api/v1/fechas-academicas/{id}       → 200

Permisos (RBAC fail-closed):
    fechas_academicas:gestionar → POST/PUT/DELETE
    fechas_academicas:ver       → GET

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.models.evaluacion import TipoFechaAcademica
from app.repositories.fecha_academica_repository import FechaAcademicaRepository
from app.schemas.fecha_academica import (
    FechaAcademicaCreate,
    FechaAcademicaRead,
    FechaAcademicaUpdate,
)
from app.services.fecha_academica_service import FechaAcademicaService

router = APIRouter(prefix="/api/v1/fechas-academicas", tags=["fechas-academicas"])


# ── Dependency factory ─────────────────────────────────────────────────────────


def _get_fecha_academica_service(
    db: AsyncSession = Depends(get_db),
) -> FechaAcademicaService:
    return FechaAcademicaService(FechaAcademicaRepository(db))


# ── POST /fechas-academicas ────────────────────────────────────────────────────


@router.post(
    "",
    response_model=FechaAcademicaRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("fechas_academicas:gestionar"))],
)
async def crear_fecha_academica(
    data: FechaAcademicaCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: FechaAcademicaService = Depends(_get_fecha_academica_service),
    db: AsyncSession = Depends(get_db),
):
    """Crea una fecha académica.

    tenant_id tomado exclusivamente del JWT.
    """
    result = await svc.crear(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return result


# ── GET /fechas-academicas ─────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[FechaAcademicaRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("fechas_academicas:ver"))],
)
async def listar_fechas_academicas(
    materia_id: Optional[uuid.UUID] = Query(None),
    cohorte_id: Optional[uuid.UUID] = Query(None),
    tipo: Optional[TipoFechaAcademica] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: FechaAcademicaService = Depends(_get_fecha_academica_service),
):
    """Lista fechas académicas del tenant con filtros opcionales."""
    return await svc.listar(
        tenant_id=current_user.tenant_id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=tipo,
    )


# ── PUT /fechas-academicas/{id} ────────────────────────────────────────────────


@router.put(
    "/{fecha_id}",
    response_model=FechaAcademicaRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("fechas_academicas:gestionar"))],
)
async def actualizar_fecha_academica(
    fecha_id: uuid.UUID,
    data: FechaAcademicaUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: FechaAcademicaService = Depends(_get_fecha_academica_service),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza una fecha académica."""
    result = await svc.actualizar(fecha_id, tenant_id=current_user.tenant_id, data=data)
    await db.commit()
    return result


# ── DELETE /fechas-academicas/{id} ────────────────────────────────────────────


@router.delete(
    "/{fecha_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("fechas_academicas:gestionar"))],
)
async def eliminar_fecha_academica(
    fecha_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: FechaAcademicaService = Depends(_get_fecha_academica_service),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete de una fecha académica."""
    await svc.eliminar(fecha_id, tenant_id=current_user.tenant_id)
    await db.commit()
    return {"ok": True}
