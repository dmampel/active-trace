import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password
from app.services.auth_service import AuthService, AuthError
from app.schemas.auth import TokenResponse, PartialTokenResponse


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def tenant(session):
    t = Tenant(name=f"T-{uuid.uuid4().hex[:6]}")
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@pytest.fixture
def active_user(session, tenant):
    u = User(
        tenant_id=tenant.id,
        email="user@example.com",
        password_hash=hash_password("correct_pass"),
        is_active=True,
        totp_enabled=False,
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


@pytest.fixture
def totp_user(session, tenant):
    import pyotp
    from app.core.security import AES256Cipher
    import base64
    key = base64.urlsafe_b64encode(b"b" * 32)
    cipher = AES256Cipher(key)
    secret = pyotp.random_base32()
    u = User(
        tenant_id=tenant.id,
        email="totp@example.com",
        password_hash=hash_password("correct_pass"),
        is_active=True,
        totp_enabled=True,
        totp_secret_enc=cipher.encrypt(secret),
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u, secret


# ── login ─────────────────────────────────────────────────────────────────────

def test_login_success_no_2fa(session, tenant, active_user):
    result = AuthService.login(session, tenant.id, "user@example.com", "correct_pass")
    assert isinstance(result, TokenResponse)
    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"


def test_login_wrong_password_raises(session, tenant, active_user):
    with pytest.raises(AuthError):
        AuthService.login(session, tenant.id, "user@example.com", "wrong_pass")


def test_login_unknown_email_raises(session, tenant):
    with pytest.raises(AuthError):
        AuthService.login(session, tenant.id, "nobody@example.com", "pass")


def test_login_inactive_user_raises(session, tenant):
    u = User(
        tenant_id=tenant.id,
        email="inactive@example.com",
        password_hash=hash_password("pass"),
        is_active=False,
    )
    session.add(u)
    session.commit()
    with pytest.raises(AuthError):
        AuthService.login(session, tenant.id, "inactive@example.com", "pass")


def test_login_with_2fa_returns_partial_token(session, tenant, totp_user):
    user, _ = totp_user
    result = AuthService.login(session, tenant.id, "totp@example.com", "correct_pass")
    assert isinstance(result, PartialTokenResponse)
    assert result.requires_2fa is True
    assert result.partial_token


# ── refresh rotation ──────────────────────────────────────────────────────────

def test_refresh_rotation_returns_new_tokens(session, tenant, active_user):
    first = AuthService.login(session, tenant.id, "user@example.com", "correct_pass")
    assert isinstance(first, TokenResponse)
    session.commit()

    second = AuthService.refresh(session, tenant.id, first.refresh_token)
    assert isinstance(second, TokenResponse)
    # New opaque refresh token must differ; access token may be identical if same second
    assert second.refresh_token != first.refresh_token


def test_refresh_reuse_raises(session, tenant, active_user):
    first = AuthService.login(session, tenant.id, "user@example.com", "correct_pass")
    assert isinstance(first, TokenResponse)
    session.commit()

    AuthService.refresh(session, tenant.id, first.refresh_token)
    session.commit()

    with pytest.raises(AuthError):
        AuthService.refresh(session, tenant.id, first.refresh_token)


# ── logout ────────────────────────────────────────────────────────────────────

def test_logout_revokes_token(session, tenant, active_user):
    tokens = AuthService.login(session, tenant.id, "user@example.com", "correct_pass")
    assert isinstance(tokens, TokenResponse)
    session.commit()

    AuthService.logout(session, tenant.id, tokens.refresh_token)
    session.commit()

    with pytest.raises(AuthError):
        AuthService.refresh(session, tenant.id, tokens.refresh_token)


def test_logout_wrong_tenant_does_not_revoke(session, tenant, active_user):
    tokens = AuthService.login(session, tenant.id, "user@example.com", "correct_pass")
    assert isinstance(tokens, TokenResponse)
    session.commit()

    other_tenant_id = uuid.uuid4()
    AuthService.logout(session, other_tenant_id, tokens.refresh_token)
    session.commit()

    # Token must still be valid — wrong tenant cannot revoke it
    result = AuthService.refresh(session, tenant.id, tokens.refresh_token)
    assert isinstance(result, TokenResponse)


# ── forgot_password ───────────────────────────────────────────────────────────

def test_forgot_password_unknown_email_does_not_raise(session, tenant):
    # Must silently succeed to avoid email enumeration
    AuthService.forgot_password(session, tenant.id, "ghost@example.com")


def test_forgot_password_known_email_creates_token(session, tenant, active_user):
    token_str = AuthService.forgot_password(session, tenant.id, "user@example.com")
    session.commit()
    assert token_str is not None


# ── reset_password ────────────────────────────────────────────────────────────

def test_reset_password_valid_token(session, tenant, active_user):
    token_str = AuthService.forgot_password(session, tenant.id, "user@example.com")
    session.commit()

    AuthService.reset_password(session, tenant.id, token_str, "new_secure_pass_123")
    session.commit()

    # Old password no longer works
    with pytest.raises(AuthError):
        AuthService.login(session, tenant.id, "user@example.com", "correct_pass")

    # New password works
    result = AuthService.login(session, tenant.id, "user@example.com", "new_secure_pass_123")
    assert isinstance(result, TokenResponse)


def test_reset_password_reuse_raises(session, tenant, active_user):
    token_str = AuthService.forgot_password(session, tenant.id, "user@example.com")
    session.commit()
    AuthService.reset_password(session, tenant.id, token_str, "new_pass_abc_123")
    session.commit()

    with pytest.raises(AuthError):
        AuthService.reset_password(session, tenant.id, token_str, "another_pass_456")


def test_reset_password_expired_token_raises(session, tenant, active_user):
    from app.core.security import hash_opaque_token, generate_opaque_token
    from app.repositories.user_repository import UserRepository

    raw = generate_opaque_token()
    exp = datetime.now(timezone.utc) - timedelta(minutes=1)  # already expired
    UserRepository.create_reset_token(session, active_user.id, tenant.id, hash_opaque_token(raw), exp)
    session.commit()

    with pytest.raises(AuthError):
        AuthService.reset_password(session, tenant.id, raw, "any_new_pass_789")
