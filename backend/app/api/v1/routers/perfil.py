"""Router de perfil propio (C-20).

Endpoints bajo /api/v1/perfil:
- GET  /  → 200 leer propio perfil con PII descifrada
- PATCH / → 200 actualizar campos editables del propio perfil

Guard: require_permission('perfil:editar') en ambos.
Identidad/tenant SIEMPRE desde get_current_user (JWT) — nunca de parámetros.
cuil: solo lectura (el schema PerfilUpdate no lo declara → 422 automático).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.schemas.perfil import PerfilRead, PerfilUpdate
from app.services.perfil_service import PerfilService

router = APIRouter(prefix="/api/v1/perfil", tags=["perfil"])

_PERM = "perfil:editar"


async def _svc(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PerfilService:
    return PerfilService(db, current_user)


@router.get(
    "",
    response_model=PerfilRead,
    dependencies=[Depends(require_permission(_PERM))],
)
async def get_perfil(svc: PerfilService = Depends(_svc)):
    """Lee el perfil del usuario autenticado. Identidad exclusivamente del JWT."""
    return await svc.leer_perfil()


@router.patch(
    "",
    response_model=PerfilRead,
    dependencies=[Depends(require_permission(_PERM))],
)
async def patch_perfil(body: PerfilUpdate, svc: PerfilService = Depends(_svc)):
    """Actualiza campos editables del propio perfil.

    cuil no es editable (no declarado en PerfilUpdate → 422 automático por extra='forbid').
    """
    return await svc.actualizar_perfil(body.model_dump(exclude_none=True))
