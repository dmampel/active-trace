"""Router de avisos institucionales (C-15).

Endpoints:
    POST   /api/v1/avisos                   → AvisoResponse (201)  [avisos:publicar]
    GET    /api/v1/avisos                   → list[AvisoResponse]  [avisos:publicar]
    GET    /api/v1/avisos/mis-avisos        → list[AvisoFeedItem]  [autenticado]
    GET    /api/v1/avisos/{id}              → AvisoResponse        [avisos:publicar]
    PATCH  /api/v1/avisos/{id}              → AvisoResponse        [avisos:publicar]
    DELETE /api/v1/avisos/{id}              → 204                  [avisos:publicar]
    POST   /api/v1/avisos/{id}/ack          → 200                  [autenticado]

IMPORTANTE: /mis-avisos debe declararse ANTES de /{id} para que FastAPI no lo
interprete como un UUID.

Permisos (RBAC fail-closed):
    avisos:publicar → CRUD de avisos (COORDINADOR, ADMIN)
    Sin permiso especial → feed mis-avisos y ack (cualquier usuario autenticado)

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.aviso_repository import AvisoRepository
from app.schemas.aviso import (
    AvisoCreate,
    AvisoFeedItem,
    AvisoResponse,
    AvisoUpdate,
)
from app.services.aviso_service import AvisoService

router = APIRouter(prefix="/api/v1/avisos", tags=["avisos"])


# ── Dependency factory ─────────────────────────────────────────────────────────


def _get_aviso_service(db: AsyncSession = Depends(get_db)) -> AvisoService:
    aviso_repo = AvisoRepository(db)
    asignacion_repo = AsignacionRepository(db)
    return AvisoService(aviso_repo=aviso_repo, asignacion_repo=asignacion_repo)


# ── POST /avisos ───────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=AvisoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("avisos:publicar"))],
)
async def crear_aviso(
    data: AvisoCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_service),
    db: AsyncSession = Depends(get_db),
):
    """Crea un aviso institucional. tenant_id tomado exclusivamente del JWT."""
    result = await svc.create_aviso(data, current_user)
    await db.commit()
    return result


# ── GET /avisos ────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[AvisoResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("avisos:publicar"))],
)
async def listar_avisos(
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_service),
):
    """Lista todos los avisos del tenant (activos e inactivos)."""
    return await svc.list_avisos(current_user)


# ── GET /avisos/mis-avisos — DEBE ir ANTES de /{id} ───────────────────────────


@router.get(
    "/mis-avisos",
    response_model=list[AvisoFeedItem],
    status_code=status.HTTP_200_OK,
)
async def mis_avisos(
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_service),
):
    """Feed personalizado: avisos vigentes y activos según rol y asignaciones del usuario."""
    return await svc.get_mis_avisos(current_user)


# ── GET /avisos/{id} ───────────────────────────────────────────────────────────


@router.get(
    "/{aviso_id}",
    response_model=AvisoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("avisos:publicar"))],
)
async def obtener_aviso(
    aviso_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_service),
):
    """Obtiene un aviso por ID con contadores derivados."""
    return await svc.get_aviso(aviso_id, current_user)


# ── PATCH /avisos/{id} ─────────────────────────────────────────────────────────


@router.patch(
    "/{aviso_id}",
    response_model=AvisoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("avisos:publicar"))],
)
async def actualizar_aviso(
    aviso_id: uuid.UUID,
    data: AvisoUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_service),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza parcialmente un aviso."""
    result = await svc.update_aviso(aviso_id, data, current_user)
    await db.commit()
    return result


# ── DELETE /avisos/{id} ────────────────────────────────────────────────────────


@router.delete(
    "/{aviso_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("avisos:publicar"))],
)
async def eliminar_aviso(
    aviso_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_service),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete de un aviso. Devuelve 204 sin body."""
    await svc.delete_aviso(aviso_id, current_user)
    await db.commit()


# ── POST /avisos/{id}/ack ──────────────────────────────────────────────────────


@router.post(
    "/{aviso_id}/ack",
    status_code=status.HTTP_200_OK,
)
async def confirmar_ack(
    aviso_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AvisoService = Depends(_get_aviso_service),
    db: AsyncSession = Depends(get_db),
):
    """Confirma lectura del aviso (idempotente). Cualquier usuario autenticado."""
    await svc.confirm_ack(aviso_id, current_user)
    await db.commit()
    return {"ok": True}
