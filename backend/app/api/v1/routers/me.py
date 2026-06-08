from typing import Any

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, get_current_user
from app.core.permissions import require_permission

router = APIRouter(prefix="/api/v1/me", tags=["users"])


@router.get("")
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> Any:
    return {
        "id": str(current_user.id),
        "tenant_id": str(current_user.tenant_id),
        "roles": current_user.roles,
    }


@router.get("/protected")
async def get_protected(
    _guard: bool = Depends(require_permission("auditoria:ver")),
) -> Any:
    return {"message": "You have access to auditoria:ver"}
