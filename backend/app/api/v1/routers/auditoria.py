"""Router del panel de auditoría y métricas (C-19).

Endpoints (todos requieren auditoria:ver — fail-closed → 403):
    GET  /api/v1/auditoria/log                     → LogCompletoResponse
    GET  /api/v1/auditoria/acciones-por-dia        → AccionesPorDiaResponse
    GET  /api/v1/auditoria/comunicaciones-por-docente → EstadoComunicacionesResponse
    GET  /api/v1/auditoria/interacciones           → InteraccionesResponse
    GET  /api/v1/auditoria/ultimas-acciones        → UltimasAccionesResponse

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
Sin lógica de negocio en el router — delega TODO al AuditoriaService.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.auditoria_repository import AuditoriaRepository
from app.schemas.auditoria import (
    AccionesPorDiaResponse,
    EstadoComunicacionesResponse,
    InteraccionesResponse,
    LogCompletoResponse,
    UltimasAccionesResponse,
)
from app.services.auditoria_service import AuditoriaService

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])


# ── Dependency factory ────────────────────────────────────────────────────────


def _get_auditoria_service(db: AsyncSession = Depends(get_db)) -> AuditoriaService:
    return AuditoriaService(
        auditoria_repo=AuditoriaRepository(db),
        asignacion_repo=AsignacionRepository(db),
    )


# ── GET /log ──────────────────────────────────────────────────────────────────


@router.get(
    "/log",
    response_model=LogCompletoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("auditoria:ver"))],
)
async def get_log(
    fecha_desde: Optional[datetime] = Query(default=None, description="Filtro de fecha/hora desde (inclusivo)"),
    fecha_hasta: Optional[datetime] = Query(default=None, description="Filtro de fecha/hora hasta (inclusivo)"),
    materia_id: Optional[uuid.UUID] = Query(default=None, description="Filtro por materia"),
    usuario_id: Optional[uuid.UUID] = Query(default=None, description="Filtro por usuario actor"),
    accion: Optional[str] = Query(default=None, description="Filtro por código de acción"),
    page: int = Query(default=1, ge=1, description="Página"),
    page_size: int = Query(default=50, ge=1, le=200, description="Ítems por página"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AuditoriaService = Depends(_get_auditoria_service),
) -> LogCompletoResponse:
    """Log completo de auditoría con filtros opcionales, paginado.

    El scope (tenant + materias) se resuelve desde el JWT; los parámetros
    tenant_id ni usuario_id de sesión no se aceptan como query params.
    """
    return await svc.get_log(
        current_user=current_user,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        materia_id=materia_id,
        usuario_id=usuario_id,
        accion=accion,
        page=page,
        page_size=page_size,
    )


# ── GET /acciones-por-dia ─────────────────────────────────────────────────────


@router.get(
    "/acciones-por-dia",
    response_model=AccionesPorDiaResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("auditoria:ver"))],
)
async def get_acciones_por_dia(
    fecha_desde: Optional[datetime] = Query(default=None),
    fecha_hasta: Optional[datetime] = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AuditoriaService = Depends(_get_auditoria_service),
) -> AccionesPorDiaResponse:
    """Serie temporal de volumen de acciones por día."""
    return await svc.get_acciones_por_dia(
        current_user=current_user,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


# ── GET /comunicaciones-por-docente ───────────────────────────────────────────


@router.get(
    "/comunicaciones-por-docente",
    response_model=EstadoComunicacionesResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("auditoria:ver"))],
)
async def get_comunicaciones_por_docente(
    current_user: CurrentUser = Depends(get_current_user),
    svc: AuditoriaService = Depends(_get_auditoria_service),
) -> EstadoComunicacionesResponse:
    """Distribución de estados de comunicaciones agrupada por docente."""
    return await svc.get_comunicaciones_por_docente(current_user=current_user)


# ── GET /interacciones ────────────────────────────────────────────────────────


@router.get(
    "/interacciones",
    response_model=InteraccionesResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("auditoria:ver"))],
)
async def get_interacciones(
    current_user: CurrentUser = Depends(get_current_user),
    svc: AuditoriaService = Depends(_get_auditoria_service),
) -> InteraccionesResponse:
    """Conteo de interacciones por docente × materia × código de acción."""
    return await svc.get_interacciones(current_user=current_user)


# ── GET /ultimas-acciones ─────────────────────────────────────────────────────


@router.get(
    "/ultimas-acciones",
    response_model=UltimasAccionesResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("auditoria:ver"))],
)
async def get_ultimas_acciones(
    limite: int = Query(
        default=0,
        ge=0,
        description="Límite de registros (0 = usar el default configurado).",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AuditoriaService = Depends(_get_auditoria_service),
) -> UltimasAccionesResponse:
    """Las N acciones más recientes con límite configurable y clamp automático."""
    return await svc.get_ultimas_acciones(
        current_user=current_user,
        limite=limite,
    )
