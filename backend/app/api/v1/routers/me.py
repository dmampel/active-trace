from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.repositories.user_repository import UserRepository
from app.repositories.rbac_repository import RbacRepository

router = APIRouter(prefix="/api/v1/me", tags=["users"])


@router.get("")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    user = await UserRepository.get_by_id(db, current_user.tenant_id, current_user.id)
    permissions = await RbacRepository.get_effective_permissions(db, current_user.id, current_user.tenant_id)
    return {
        "id": str(current_user.id),
        "tenant_id": str(current_user.tenant_id),
        "email": user.email if user else "",
        "nombre": (user.nombre or "") if user else "",
        "apellidos": (user.apellidos or "") if user else "",
        "roles": current_user.roles,
        "permissions": list(permissions),
    }


@router.get("/protected")
async def get_protected(
    _guard: bool = Depends(require_permission("auditoria:ver")),
) -> Any:
    return {"message": "You have access to auditoria:ver"}
