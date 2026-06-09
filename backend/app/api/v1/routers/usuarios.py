"""Router de gestión de usuarios.

Endpoints bajo /api/v1/usuarios:
- POST   /         → 201 crear usuario
- GET    /         → 200 listar (sin PII)
- GET    /{id}     → 200 detalle (con PII descifrada)
- PATCH  /{id}     → 200 actualizar
- DELETE /{id}     → 204 soft delete

Guard: require_permission("usuarios:gestionar") en todos los endpoints.
Identidad/tenant SIEMPRE desde get_current_user (JWT).
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.schemas.usuario import UsuarioCreate, UsuarioDetail, UsuarioListItem, UsuarioUpdate
from app.services.usuario_service import UsuarioService

router = APIRouter(prefix="/api/v1/usuarios", tags=["usuarios"])

_PERM = "usuarios:gestionar"


async def _svc(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsuarioService:
    return UsuarioService(db, current_user, request)


@router.post(
    "",
    response_model=UsuarioListItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(_PERM))],
)
async def create_usuario(body: UsuarioCreate, svc: UsuarioService = Depends(_svc)):
    return await svc.create(body.model_dump())


@router.get(
    "",
    response_model=List[UsuarioListItem],
    dependencies=[Depends(require_permission(_PERM))],
)
async def list_usuarios(svc: UsuarioService = Depends(_svc)):
    return await svc.list_users()


@router.get(
    "/{id}",
    response_model=UsuarioDetail,
    dependencies=[Depends(require_permission(_PERM))],
)
async def get_usuario(id: uuid.UUID, svc: UsuarioService = Depends(_svc)):
    return await svc.get_detail(id)


@router.patch(
    "/{id}",
    response_model=UsuarioListItem,
    dependencies=[Depends(require_permission(_PERM))],
)
async def update_usuario(id: uuid.UUID, body: UsuarioUpdate, svc: UsuarioService = Depends(_svc)):
    return await svc.update(id, body.model_dump(exclude_none=True))


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(_PERM))],
)
async def delete_usuario(id: uuid.UUID, svc: UsuarioService = Depends(_svc)):
    await svc.soft_delete(id)
