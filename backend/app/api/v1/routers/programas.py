"""Router de programas de materia (C-17).

Endpoints:
    POST   /api/v1/programas            → ProgramaMateriaOut (201)  [estructura:gestionar]
    GET    /api/v1/programas            → list[ProgramaMateriaOut]  [estructura:leer]
    GET    /api/v1/programas/{id}       → ProgramaMateriaOut (200)  [estructura:leer]
    PATCH  /api/v1/programas/{id}       → ProgramaMateriaOut (200)  [estructura:gestionar]
    DELETE /api/v1/programas/{id}       → 204                       [estructura:gestionar]

Permisos (RBAC fail-closed):
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
from app.repositories.programa_materia_repository import ProgramaMateriaRepository
from app.schemas.programa_materia import (
    ProgramaMateriaCreate,
    ProgramaMateriaOut,
    ProgramaMateriaUpdate,
)
from app.services.programa_materia_service import ProgramaMateriaService

router = APIRouter(prefix="/api/v1/programas", tags=["programas"])


# ── Dependency factory ─────────────────────────────────────────────────────────


def _get_programa_service(
    db: AsyncSession = Depends(get_db),
) -> ProgramaMateriaService:
    return ProgramaMateriaService(ProgramaMateriaRepository(db))


# ── POST /programas ────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ProgramaMateriaOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def crear_programa(
    data: ProgramaMateriaCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProgramaMateriaService = Depends(_get_programa_service),
    db: AsyncSession = Depends(get_db),
):
    """Crea un programa de materia. tenant_id tomado exclusivamente del JWT."""
    result = await svc.crear(current_user.tenant_id, data)
    await db.commit()
    return result


# ── GET /programas ─────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[ProgramaMateriaOut],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("estructura:leer"))],
)
async def listar_programas(
    materia_id: Optional[uuid.UUID] = Query(None),
    carrera_id: Optional[uuid.UUID] = Query(None),
    cohorte_id: Optional[uuid.UUID] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProgramaMateriaService = Depends(_get_programa_service),
):
    """Lista programas del tenant con filtros opcionales por contexto académico."""
    if materia_id and carrera_id and cohorte_id:
        # Búsqueda exacta por contexto completo
        programa = await svc.get_by_context(
            current_user.tenant_id, materia_id, carrera_id, cohorte_id
        )
        return [programa] if programa else []
    # Sin filtros completos: devuelve lista vacía (el contexto completo es necesario)
    # En futuras versiones se puede ampliar a búsquedas parciales.
    return []


# ── GET /programas/{id} ────────────────────────────────────────────────────────


@router.get(
    "/{programa_id}",
    response_model=ProgramaMateriaOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("estructura:leer"))],
)
async def obtener_programa(
    programa_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProgramaMateriaService = Depends(_get_programa_service),
):
    """Obtiene un programa de materia por ID."""
    return await svc.get_by_id(current_user.tenant_id, programa_id)


# ── PATCH /programas/{id} ──────────────────────────────────────────────────────


@router.patch(
    "/{programa_id}",
    response_model=ProgramaMateriaOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def actualizar_programa(
    programa_id: uuid.UUID,
    data: ProgramaMateriaUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProgramaMateriaService = Depends(_get_programa_service),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza título o referencia de archivo de un programa."""
    result = await svc.actualizar(current_user.tenant_id, programa_id, data)
    await db.commit()
    return result


# ── DELETE /programas/{id} ────────────────────────────────────────────────────


@router.delete(
    "/{programa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def eliminar_programa(
    programa_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProgramaMateriaService = Depends(_get_programa_service),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete de un programa de materia."""
    await svc.eliminar(current_user.tenant_id, programa_id)
    await db.commit()
