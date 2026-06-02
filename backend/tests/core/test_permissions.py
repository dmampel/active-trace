import uuid
import pytest
from fastapi import HTTPException
from app.core.permissions import has_permission, require_permission
from app.core.dependencies import CurrentUser
from unittest.mock import MagicMock

def test_has_permission():
    effective = {"modulo:accion1", "modulo:accion2"}
    assert has_permission(effective, "modulo:accion1") is True
    assert has_permission(effective, "modulo:accion3") is False

def test_require_permission_returns_403_when_user_lacks_permission():
    # Setup mock dependencies
    mock_session = MagicMock()
    user = CurrentUser(id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=["R1"])
    
    # Create the dependency generator
    dependency = require_permission("modulo:protegido")
    
    # We mock RbacRepository.get_effective_permissions to return an empty set
    with pytest.raises(HTTPException) as exc_info:
        # We need to patch the repository so it returns empty
        with pytest.MonkeyPatch.context() as m:
            m.setattr("app.core.permissions.RbacRepository.get_effective_permissions", lambda s, u, t: {"otro:permiso"})
            dependency(current_user=user, session=mock_session)
    
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden: missing permission modulo:protegido"

def test_require_permission_passes_when_user_has_permission():
    mock_session = MagicMock()
    user = CurrentUser(id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=["R1"])
    dependency = require_permission("modulo:protegido")
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.core.permissions.RbacRepository.get_effective_permissions", lambda s, u, t: {"modulo:protegido"})
        # Should not raise exception
        dependency(current_user=user, session=mock_session)

def test_require_permission_fail_closed_unknown_permission():
    mock_session = MagicMock()
    user = CurrentUser(id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=["ADMIN"])
    dependency = require_permission("desconocido:accion")
    
    with pytest.MonkeyPatch.context() as m:
        # Even if they have many permissions, if they don't have the specific one, it fails closed
        m.setattr("app.core.permissions.RbacRepository.get_effective_permissions", lambda s, u, t: {"otro:permiso"})
        with pytest.raises(HTTPException) as exc_info:
            dependency(current_user=user, session=mock_session)
        assert exc_info.value.status_code == 403
