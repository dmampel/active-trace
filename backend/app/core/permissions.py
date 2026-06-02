from typing import Callable, Set
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, get_current_user, get_sync_db
from app.repositories.rbac_repository import RbacRepository

def has_permission(effective: Set[str], permission: str) -> bool:
    return permission in effective

def require_permission(permission: str) -> Callable:
    """Guard RBAC: verifica permiso modulo:accion. Sin él → 403 (fail-closed)."""
    def permission_checker(
        current_user: CurrentUser = Depends(get_current_user),
        session: Session = Depends(get_sync_db),
    ):
        effective_perms = RbacRepository.get_effective_permissions(
            session, current_user.id, current_user.tenant_id
        )
        if not has_permission(effective_perms, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: missing permission {permission}",
            )
        return True
    return permission_checker
