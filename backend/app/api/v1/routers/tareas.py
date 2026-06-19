"""Router de tareas internas (C-16).

Endpoints:
    POST   /api/v1/tareas                          → TareaOut (201)    [tareas:gestionar]
    GET    /api/v1/tareas/mis-tareas               → list[TareaOut]    [tareas:gestionar]
    GET    /api/v1/tareas                          → PaginatedTareas   [tareas:gestionar + COORD/ADMIN]
    PATCH  /api/v1/tareas/{tarea_id}/estado        → TareaOut (200)    [tareas:gestionar]
    POST   /api/v1/tareas/{tarea_id}/comentarios   → ComentarioOut (201) [tareas:gestionar]
    GET    /api/v1/tareas/{tarea_id}/comentarios   → list[ComentarioOut] [tareas:gestionar]

IMPORTANTE: /mis-tareas debe declararse ANTES de /{tarea_id} para que FastAPI
no lo interprete como un UUID.

Permisos (RBAC fail-closed):
    tareas:gestionar → requerido en todos los endpoints
    Vista global GET /tareas → adicionalmente requiere rol COORDINADOR o ADMIN
                               (validado en el servicio con PermissionError → 403)

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.models.tarea import EstadoTarea
from app.repositories.tarea_repository import ComentarioTareaRepository, TareaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.tarea import (
    ComentarioCreate,
    ComentarioOut,
    PaginatedTareas,
    TareaCreate,
    TareaEstadoUpdate,
    TareaOut,
)
from app.services.tarea_service import TareaService

router = APIRouter(prefix="/api/v1/tareas", tags=["tareas"])


# ── Dependency factory ─────────────────────────────────────────────────────────


def _get_tarea_service(db: AsyncSession = Depends(get_db)) -> TareaService:
    tarea_repo = TareaRepository(db)
    comentario_repo = ComentarioTareaRepository(db)
    usuario_repo = UsuarioRepository(db)
    return TareaService(
        tarea_repo=tarea_repo,
        comentario_repo=comentario_repo,
        usuario_repo=usuario_repo,
    )


# ── POST /tareas ───────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=TareaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tareas:gestionar"))],
)
async def crear_tarea(
    data: TareaCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_service),
    db: AsyncSession = Depends(get_db),
):
    """Crea una tarea interna. tenant_id y asignado_por tomados del JWT."""
    result = await svc.crear_tarea(current_user.tenant_id, current_user.id, data)
    await db.commit()
    return result


# ── GET /tareas/mis-tareas — DEBE ir ANTES de /{tarea_id} ─────────────────────


@router.get(
    "/mis-tareas",
    response_model=list[TareaOut],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("tareas:gestionar"))],
)
async def mis_tareas(
    estado: Optional[EstadoTarea] = None,
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_service),
):
    """Lista las tareas asignadas al usuario autenticado, filtradas por estado (opcional)."""
    return await svc.mis_tareas(current_user.tenant_id, current_user.id, estado)


# ── GET /tareas — vista global admin ──────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedTareas,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("tareas:gestionar"))],
)
async def listar_tareas(
    page: int = 1,
    size: int = 50,
    estado: Optional[EstadoTarea] = None,
    asignado_a: Optional[uuid.UUID] = None,
    asignado_por: Optional[uuid.UUID] = None,
    materia_id: Optional[uuid.UUID] = None,
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_service),
):
    """Vista paginada de todas las tareas del tenant. Solo COORDINADOR/ADMIN."""
    filters: dict = {}
    if estado is not None:
        filters["estado"] = estado
    if asignado_a is not None:
        filters["asignado_a"] = asignado_a
    if asignado_por is not None:
        filters["asignado_por"] = asignado_por
    if materia_id is not None:
        filters["materia_id"] = materia_id

    try:
        return await svc.listar_todas(
            current_user.tenant_id, current_user.roles, filters, page, size
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


# ── PATCH /tareas/{tarea_id}/estado ───────────────────────────────────────────


@router.patch(
    "/{tarea_id}/estado",
    response_model=TareaOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("tareas:gestionar"))],
)
async def cambiar_estado(
    tarea_id: uuid.UUID,
    data: TareaEstadoUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_service),
    db: AsyncSession = Depends(get_db),
):
    """Cambia el estado de una tarea. Valida transición y autorización."""
    try:
        result = await svc.cambiar_estado(
            current_user.tenant_id,
            tarea_id,
            data.estado,
            current_user.id,
            current_user.roles,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    await db.commit()
    return result


# ── POST /tareas/{tarea_id}/comentarios ───────────────────────────────────────


@router.post(
    "/{tarea_id}/comentarios",
    response_model=ComentarioOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tareas:gestionar"))],
)
async def agregar_comentario(
    tarea_id: uuid.UUID,
    data: ComentarioCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_service),
    db: AsyncSession = Depends(get_db),
):
    """Agrega un comentario a una tarea (append-only)."""
    result = await svc.agregar_comentario(
        current_user.tenant_id, tarea_id, current_user.id, data.texto
    )
    await db.commit()
    return result


# ── GET /tareas/{tarea_id}/comentarios ────────────────────────────────────────


@router.get(
    "/{tarea_id}/comentarios",
    response_model=list[ComentarioOut],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("tareas:gestionar"))],
)
async def listar_comentarios(
    tarea_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: TareaService = Depends(_get_tarea_service),
):
    """Lista los comentarios de una tarea en orden cronológico."""
    return await svc.listar_comentarios(current_user.tenant_id, tarea_id)
