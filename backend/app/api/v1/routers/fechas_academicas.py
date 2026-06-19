"""Router de fechas académicas (C-14 / C-17).

Endpoints:
    POST   /api/v1/fechas-academicas                → FechaAcademicaRead (201)
    GET    /api/v1/fechas-academicas                → list[FechaAcademicaRead]
    GET    /api/v1/fechas-academicas/lms-fragment   → LMSFragmentOut
    GET    /api/v1/fechas-academicas/{id}           → FechaAcademicaRead (200 o 404)
    PATCH  /api/v1/fechas-academicas/{id}           → FechaAcademicaRead (200)
    DELETE /api/v1/fechas-academicas/{id}           → 204

IMPORTANTE: /lms-fragment debe declararse ANTES de /{fecha_id} para que FastAPI
no lo interprete como un UUID.

Permisos (C-17, RBAC fail-closed):
    estructura:gestionar → POST/PATCH/DELETE
    estructura:leer      → GET

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.repositories.fecha_academica_repository import FechaAcademicaRepository
from app.schemas.fecha_academica import (
    FechaAcademicaCreate,
    FechaAcademicaRead,
    FechaAcademicaUpdate,
    LMSFragmentOut,
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
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def crear_fecha_academica(
    data: FechaAcademicaCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: FechaAcademicaService = Depends(_get_fecha_academica_service),
    db: AsyncSession = Depends(get_db),
):
    """Crea una fecha académica. tenant_id tomado exclusivamente del JWT."""
    result = await svc.crear(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return result


# ── GET /fechas-academicas ─────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[FechaAcademicaRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("estructura:leer"))],
)
async def listar_fechas_academicas(
    materia_id: Optional[uuid.UUID] = Query(None),
    cohorte_id: Optional[uuid.UUID] = Query(None),
    periodo: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: FechaAcademicaService = Depends(_get_fecha_academica_service),
):
    """Lista fechas académicas del tenant con filtros opcionales."""
    return await svc.listar(
        tenant_id=current_user.tenant_id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        periodo=periodo,
    )


# ── GET /fechas-academicas/lms-fragment — DEBE ir ANTES de /{fecha_id} ────────


@router.get(
    "/lms-fragment",
    response_model=LMSFragmentOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("estructura:leer"))],
)
async def generar_fragmento_lms(
    materia_id: uuid.UUID = Query(...),
    cohorte_id: uuid.UUID = Query(...),
    periodo: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: FechaAcademicaService = Depends(_get_fecha_academica_service),
):
    """Genera un fragmento Markdown con las fechas del período para el LMS."""
    return await svc.generar_fragmento_lms(
        tenant_id=current_user.tenant_id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        periodo=periodo,
    )


# ── GET /fechas-academicas/{id} ────────────────────────────────────────────────


@router.get(
    "/{fecha_id}",
    response_model=FechaAcademicaRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("estructura:leer"))],
)
async def obtener_fecha_academica(
    fecha_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: FechaAcademicaService = Depends(_get_fecha_academica_service),
):
    """Obtiene una fecha académica por ID."""
    return await svc.get_by_id(current_user.tenant_id, fecha_id)


# ── PATCH /fechas-academicas/{id} ─────────────────────────────────────────────


@router.patch(
    "/{fecha_id}",
    response_model=FechaAcademicaRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("estructura:gestionar"))],
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
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("estructura:gestionar"))],
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
