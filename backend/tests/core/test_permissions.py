import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.dependencies import CurrentUser
from app.core.permissions import has_permission, require_permission


def test_has_permission():
    effective = {"modulo:accion1", "modulo:accion2"}
    assert has_permission(effective, "modulo:accion1") is True
    assert has_permission(effective, "modulo:accion3") is False


async def test_require_permission_returns_403_when_user_lacks_permission(monkeypatch):
    user = CurrentUser(id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=["R1"])

    mock_perms = AsyncMock(return_value={"otro:permiso"})
    monkeypatch.setattr("app.core.permissions.RbacRepository.get_effective_permissions", mock_perms)

    dependency_fn = require_permission("modulo:protegido")
    with pytest.raises(HTTPException) as exc_info:
        await dependency_fn(current_user=user, session=AsyncMock())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden: missing permission modulo:protegido"


async def test_require_permission_passes_when_user_has_permission(monkeypatch):
    user = CurrentUser(id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=["R1"])

    mock_perms = AsyncMock(return_value={"modulo:protegido"})
    monkeypatch.setattr("app.core.permissions.RbacRepository.get_effective_permissions", mock_perms)

    dependency_fn = require_permission("modulo:protegido")
    result = await dependency_fn(current_user=user, session=AsyncMock())
    assert result is True


async def test_require_permission_fail_closed_unknown_permission(monkeypatch):
    user = CurrentUser(id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=["ADMIN"])

    mock_perms = AsyncMock(return_value={"otro:permiso"})
    monkeypatch.setattr("app.core.permissions.RbacRepository.get_effective_permissions", mock_perms)

    dependency_fn = require_permission("desconocido:accion")
    with pytest.raises(HTTPException) as exc_info:
        await dependency_fn(current_user=user, session=AsyncMock())
    assert exc_info.value.status_code == 403
