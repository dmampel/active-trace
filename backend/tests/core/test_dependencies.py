import uuid
import pytest
from datetime import timedelta
from unittest.mock import MagicMock

from app.core.security import create_access_token, create_partial_token
from app.core.dependencies import get_current_user, CurrentUser


def _make_token(user_id: str, tenant_id: str, roles: list[str]) -> str:
    return create_access_token(
        {"sub": user_id, "tenant_id": tenant_id, "roles": roles},
        expires_delta=timedelta(minutes=15),
    )


def test_get_current_user_valid_token():
    uid = str(uuid.uuid4())
    tid = str(uuid.uuid4())
    token = _make_token(uid, tid, ["PROFESOR"])

    result = get_current_user(token=token)

    assert isinstance(result, CurrentUser)
    assert str(result.id) == uid
    assert str(result.tenant_id) == tid
    assert result.roles == ["PROFESOR"]


def test_get_current_user_expired_token():
    from fastapi import HTTPException
    uid = str(uuid.uuid4())
    token = create_access_token(
        {"sub": uid, "tenant_id": str(uuid.uuid4()), "roles": []},
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)
    assert exc_info.value.status_code == 401


def test_get_current_user_invalid_token():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="not.a.valid.token")
    assert exc_info.value.status_code == 401


def test_get_current_user_ignores_body_params():
    uid = str(uuid.uuid4())
    tid = str(uuid.uuid4())
    token = _make_token(uid, tid, ["ADMIN"])

    # Identity must come from JWT, not from any other source
    result = get_current_user(token=token)
    assert str(result.id) == uid
    assert str(result.tenant_id) == tid


def test_partial_token_not_valid_for_get_current_user():
    from fastapi import HTTPException
    partial = create_partial_token(str(uuid.uuid4()), str(uuid.uuid4()))
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=partial)
    assert exc_info.value.status_code == 401
