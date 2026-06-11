"""Router de asignaciones contextuales.

Endpoints bajo /api/v1/asignaciones:
- POST   /         → 201 crear asignación
- GET    /         → 200 listar con filtros
- GET    /{id}     → 200 detalle
- PATCH  /{id}     → 200 actualizar
- DELETE /{id}     → 204 soft delete

Guard: require_permission("equipos:asignar") en todos los endpoints.
Identidad/tenant SIEMPRE desde get_current_user (JWT).
Auditoría ASIGNACION_MODIFICAR en create/update/delete.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.schemas.asignacion import AsignacionCreate, AsignacionRead, AsignacionUpdate
from app.services.asignacion_service import AsignacionService

router = APIRouter(prefix="/api/v1/asignaciones", tags=["asignaciones"])

_PERM = "equipos:asignar"


async def _svc(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsignacionService:
    return AsignacionService(db, current_user, request)


@router.post(
    "",
    response_model=AsignacionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(_PERM))],
)
async def create_asignacion(body: AsignacionCreate, svc: AsignacionService = Depends(_svc)):
    return await svc.create(body.model_dump())


@router.get(
    "",
    response_model=List[AsignacionRead],
    dependencies=[Depends(require_permission(_PERM))],
)
async def list_asignaciones(
    usuario_id: Optional[uuid.UUID] = None,
    materia_id: Optional[uuid.UUID] = None,
    cohorte_id: Optional[uuid.UUID] = None,
    carrera_id: Optional[uuid.UUID] = None,
    rol: Optional[str] = None,
    vigente_only: bool = False,
    svc: AsignacionService = Depends(_svc),
):
    return await svc.list_asignaciones(
        usuario_id=usuario_id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        carrera_id=carrera_id,
        rol=rol,
        vigente_only=vigente_only,
    )


@router.get(
    "/{id}",
    response_model=AsignacionRead,
    dependencies=[Depends(require_permission(_PERM))],
)
async def get_asignacion(id: uuid.UUID, svc: AsignacionService = Depends(_svc)):
    return await svc.get_detail(id)


@router.patch(
    "/{id}",
    response_model=AsignacionRead,
    dependencies=[Depends(require_permission(_PERM))],
)
async def update_asignacion(
    id: uuid.UUID, body: AsignacionUpdate, svc: AsignacionService = Depends(_svc)
):
    return await svc.update(id, body.model_dump(exclude_none=True))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(_PERM))],
)
async def delete_asignacion(id: uuid.UUID, svc: AsignacionService = Depends(_svc)):
    await svc.soft_delete(id)
