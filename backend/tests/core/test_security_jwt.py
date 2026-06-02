import time
import pytest
from datetime import timedelta

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_partial_token,
    decode_token,
    hash_opaque_token,
    InvalidTokenError,
)


# ── hash_password / verify_password ──────────────────────────────────────────

def test_hash_password_returns_different_from_plain():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert isinstance(hashed, str)


def test_verify_password_correct():
    hashed = hash_password("correct_password")
    assert verify_password("correct_password", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct_password")
    assert verify_password("wrong_password", hashed) is False


# ── create_access_token / decode_token ───────────────────────────────────────

def test_access_token_round_trip():
    payload = {"sub": "user-id-123", "tenant_id": "tenant-xyz", "roles": ["PROFESOR"]}
    token = create_access_token(payload, expires_delta=timedelta(minutes=15))
    decoded = decode_token(token)
    assert decoded["sub"] == "user-id-123"
    assert decoded["tenant_id"] == "tenant-xyz"
    assert decoded["roles"] == ["PROFESOR"]


def test_access_token_expired_raises():
    payload = {"sub": "user-id-123", "tenant_id": "t", "roles": []}
    token = create_access_token(payload, expires_delta=timedelta(seconds=-1))
    with pytest.raises(InvalidTokenError):
        decode_token(token)


def test_access_token_tampered_raises():
    payload = {"sub": "user-id-123", "tenant_id": "t", "roles": []}
    token = create_access_token(payload, expires_delta=timedelta(minutes=15))
    tampered = token[:-4] + "XXXX"
    with pytest.raises(InvalidTokenError):
        decode_token(tampered)


# ── create_partial_token ─────────────────────────────────────────────────────

def test_partial_token_has_correct_scope():
    token = create_partial_token("uid-1", "tenant-1")
    decoded = decode_token(token)
    assert decoded["scope"] == "2fa_pending"
    assert decoded["sub"] == "uid-1"
    assert decoded["tenant_id"] == "tenant-1"


def test_partial_token_missing_scope_not_treated_as_access():
    payload = {"sub": "u", "tenant_id": "t", "roles": ["ADMIN"]}
    access = create_access_token(payload, expires_delta=timedelta(minutes=15))
    decoded = decode_token(access)
    assert decoded.get("scope") != "2fa_pending"


# ── hash_opaque_token ────────────────────────────────────────────────────────

def test_hash_opaque_token_deterministic():
    token = "my-secret-opaque-token"
    h1 = hash_opaque_token(token)
    h2 = hash_opaque_token(token)
    assert h1 == h2
    assert h1 != token


def test_hash_opaque_token_different_inputs_differ():
    assert hash_opaque_token("token-a") != hash_opaque_token("token-b")
