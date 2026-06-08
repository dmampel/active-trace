"""Tests de AuthService — suite async sobre PostgreSQL real."""
import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from app.core.security import AES256GCMCipher, create_partial_token, decode_token, generate_opaque_token, hash_opaque_token, hash_password
from app.models.rbac import Rol, UserRol
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import PartialTokenResponse, TokenResponse
from app.services.auth_service import AuthError, AuthService


# ── Key idéntica a la que usa auth_service en runtime ─────────────────────────
_CIPHER = AES256GCMCipher(hashlib.sha256(("b" * 64).encode()).digest())


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    t = Tenant(name=f"T-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def active_user(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id,
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("correct_pass"),
        is_active=True,
        totp_enabled=False,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def totp_user(db_session: AsyncSession, tenant: Tenant):
    secret = pyotp.random_base32()
    u = User(
        tenant_id=tenant.id,
        email=f"totp-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("correct_pass"),
        is_active=True,
        totp_enabled=True,
        totp_secret_enc=_CIPHER.encrypt(secret),
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u, secret


# ── login ──────────────────────────────────────────────────────────────────────

async def test_login_success_no_2fa(db_session: AsyncSession, tenant: Tenant, active_user: User):
    result = await AuthService.login(db_session, tenant.id, active_user.email, "correct_pass")
    assert isinstance(result, TokenResponse)
    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"
    claims = decode_token(result.access_token)
    assert "roles" in claims
    assert claims["roles"] == []


async def test_login_case_insensitive_email(db_session: AsyncSession, tenant: Tenant, active_user: User):
    result = await AuthService.login(db_session, tenant.id, active_user.email.upper(), "correct_pass")
    assert isinstance(result, TokenResponse)


async def test_login_includes_roles_in_jwt(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from datetime import date
    rol = Rol(id=uuid.uuid4(), nombre=f"ADMIN-{uuid.uuid4().hex[:4]}")
    db_session.add(rol)
    await db_session.flush()
    db_session.add(UserRol(user_id=active_user.id, rol_id=rol.id, tenant_id=tenant.id, desde=date.today()))
    await db_session.commit()

    result = await AuthService.login(db_session, tenant.id, active_user.email, "correct_pass")
    claims = decode_token(result.access_token)
    assert rol.nombre in claims["roles"]


async def test_login_wrong_password_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    with pytest.raises(AuthError):
        await AuthService.login(db_session, tenant.id, active_user.email, "wrong_pass")


async def test_login_unknown_email_raises(db_session: AsyncSession, tenant: Tenant):
    with pytest.raises(AuthError):
        await AuthService.login(db_session, tenant.id, "nobody@example.com", "pass")


async def test_login_inactive_user_raises(db_session: AsyncSession, tenant: Tenant):
    email = f"inactive-{uuid.uuid4().hex[:6]}@example.com"
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password("pass"),
        is_active=False,
    )
    db_session.add(u)
    await db_session.commit()
    with pytest.raises(AuthError):
        await AuthService.login(db_session, tenant.id, email, "pass")


async def test_login_with_2fa_returns_partial_token(db_session: AsyncSession, tenant: Tenant, totp_user):
    user, _ = totp_user
    result = await AuthService.login(db_session, tenant.id, user.email, "correct_pass")
    assert isinstance(result, PartialTokenResponse)
    assert result.requires_2fa is True
    assert result.partial_token


# ── refresh rotation ───────────────────────────────────────────────────────────

async def test_refresh_rotation_returns_new_tokens(db_session: AsyncSession, tenant: Tenant, active_user: User):
    first = await AuthService.login(db_session, tenant.id, active_user.email, "correct_pass")
    assert isinstance(first, TokenResponse)
    await db_session.commit()

    second = await AuthService.refresh(db_session, tenant.id, first.refresh_token)
    assert isinstance(second, TokenResponse)
    assert second.refresh_token != first.refresh_token


async def test_refresh_token_contains_updated_roles(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from datetime import date
    first = await AuthService.login(db_session, tenant.id, active_user.email, "correct_pass")
    assert isinstance(first, TokenResponse)
    assert decode_token(first.access_token)["roles"] == []
    await db_session.commit()

    rol = Rol(id=uuid.uuid4(), nombre=f"COORDINADOR-{uuid.uuid4().hex[:4]}")
    db_session.add(rol)
    await db_session.flush()
    db_session.add(UserRol(user_id=active_user.id, rol_id=rol.id, tenant_id=tenant.id, desde=date.today()))
    await db_session.commit()

    second = await AuthService.refresh(db_session, tenant.id, first.refresh_token)
    assert isinstance(second, TokenResponse)
    assert rol.nombre in decode_token(second.access_token)["roles"]


async def test_refresh_reuse_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    first = await AuthService.login(db_session, tenant.id, active_user.email, "correct_pass")
    assert isinstance(first, TokenResponse)
    await db_session.commit()

    await AuthService.refresh(db_session, tenant.id, first.refresh_token)
    await db_session.commit()

    with pytest.raises(AuthError):
        await AuthService.refresh(db_session, tenant.id, first.refresh_token)


# ── logout ─────────────────────────────────────────────────────────────────────

async def test_logout_revokes_token(db_session: AsyncSession, tenant: Tenant, active_user: User):
    tokens = await AuthService.login(db_session, tenant.id, active_user.email, "correct_pass")
    assert isinstance(tokens, TokenResponse)
    await db_session.commit()

    await AuthService.logout(db_session, tenant.id, tokens.refresh_token)
    await db_session.commit()

    with pytest.raises(AuthError):
        await AuthService.refresh(db_session, tenant.id, tokens.refresh_token)


async def test_logout_wrong_tenant_does_not_revoke(db_session: AsyncSession, tenant: Tenant, active_user: User):
    tokens = await AuthService.login(db_session, tenant.id, active_user.email, "correct_pass")
    assert isinstance(tokens, TokenResponse)
    await db_session.commit()

    other_tenant_id = uuid.uuid4()
    await AuthService.logout(db_session, other_tenant_id, tokens.refresh_token)
    await db_session.commit()

    # Token debe seguir siendo válido — tenant incorrecto no puede revocarlo
    result = await AuthService.refresh(db_session, tenant.id, tokens.refresh_token)
    assert isinstance(result, TokenResponse)


# ── forgot_password / reset_password ──────────────────────────────────────────

async def test_forgot_password_unknown_email_does_not_raise(db_session: AsyncSession, tenant: Tenant):
    # Silencioso para no enumerar emails
    await AuthService.forgot_password(db_session, tenant.id, "ghost@example.com")


async def test_forgot_password_known_email_creates_token(db_session: AsyncSession, tenant: Tenant, active_user: User):
    token_str = await AuthService.forgot_password(db_session, tenant.id, active_user.email)
    await db_session.commit()
    assert token_str is not None


async def test_reset_password_valid_token(db_session: AsyncSession, tenant: Tenant, active_user: User):
    token_str = await AuthService.forgot_password(db_session, tenant.id, active_user.email)
    await db_session.commit()

    await AuthService.reset_password(db_session, tenant.id, token_str, "new_secure_pass_123")
    await db_session.commit()

    with pytest.raises(AuthError):
        await AuthService.login(db_session, tenant.id, active_user.email, "correct_pass")

    result = await AuthService.login(db_session, tenant.id, active_user.email, "new_secure_pass_123")
    assert isinstance(result, TokenResponse)


async def test_reset_password_reuse_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    token_str = await AuthService.forgot_password(db_session, tenant.id, active_user.email)
    await db_session.commit()

    await AuthService.reset_password(db_session, tenant.id, token_str, "pass_abc_123")
    await db_session.commit()

    with pytest.raises(AuthError):
        await AuthService.reset_password(db_session, tenant.id, token_str, "pass_another_456")


async def test_reset_password_expired_token_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from app.repositories.user_repository import UserRepository

    raw = generate_opaque_token()
    exp = datetime.now(timezone.utc) - timedelta(minutes=1)
    await UserRepository.create_reset_token(db_session, active_user.id, tenant.id, hash_opaque_token(raw), exp)
    await db_session.commit()

    with pytest.raises(AuthError):
        await AuthService.reset_password(db_session, tenant.id, raw, "any_new_pass_789")


# ── impersonate ────────────────────────────────────────────────────────────────

async def test_impersonate_success_service(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from app.core.dependencies import CurrentUser

    target = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"target-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("pass"),
        is_active=True,
    )
    db_session.add(target)
    await db_session.commit()

    actor = CurrentUser(id=active_user.id, tenant_id=tenant.id, roles=[], impersonado_id=None)
    token = await AuthService.impersonate(db_session, actor, target.id)
    assert token
    claims = decode_token(token)
    assert claims["impersonado_id"] == str(target.id)
    assert claims["sub"] == str(active_user.id)


async def test_impersonate_nested_rejected_service(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from app.core.dependencies import CurrentUser

    target_id = uuid.uuid4()
    actor = CurrentUser(id=active_user.id, tenant_id=tenant.id, roles=[], impersonado_id=target_id)
    with pytest.raises(AuthError, match="impersonación activa"):
        await AuthService.impersonate(db_session, actor, uuid.uuid4())


async def test_impersonate_cross_tenant_raises_service(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from app.core.dependencies import CurrentUser

    actor = CurrentUser(id=active_user.id, tenant_id=tenant.id, roles=[], impersonado_id=None)
    with pytest.raises(AuthError):
        await AuthService.impersonate(db_session, actor, uuid.uuid4())


async def test_end_impersonation_success_service(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from app.core.dependencies import CurrentUser
    from app.models.audit_log import AuditLog
    from sqlalchemy import select

    target = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"end-target-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("pass"),
        is_active=True,
    )
    db_session.add(target)
    await db_session.commit()

    actor = CurrentUser(id=active_user.id, tenant_id=tenant.id, roles=[], impersonado_id=target.id)
    await AuthService.end_impersonation(db_session, actor)
    await db_session.commit()

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.actor_id == active_user.id)
    )
    log = result.scalar_one_or_none()
    assert log is not None


async def test_end_impersonation_no_session_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from app.core.dependencies import CurrentUser

    actor = CurrentUser(id=active_user.id, tenant_id=tenant.id, roles=[], impersonado_id=None)
    with pytest.raises(AuthError, match="impersonación activa"):
        await AuthService.end_impersonation(db_session, actor)


# ── refresh edge cases ─────────────────────────────────────────────────────────

async def test_refresh_invalid_token_raises(db_session: AsyncSession, tenant: Tenant):
    with pytest.raises(AuthError):
        await AuthService.refresh(db_session, tenant.id, "totally_invalid_token_string_xyz")


async def test_refresh_expired_token_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from app.repositories.user_repository import UserRepository

    raw = generate_opaque_token()
    family_id = uuid.uuid4()
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await UserRepository.create_refresh_token(
        db_session, active_user.id, tenant.id, hash_opaque_token(raw), family_id, expired_at
    )
    await db_session.commit()

    with pytest.raises(AuthError):
        await AuthService.refresh(db_session, tenant.id, raw)


# ── TOTP enroll ────────────────────────────────────────────────────────────────

async def test_totp_enroll_success(db_session: AsyncSession, tenant: Tenant, active_user: User):
    result = await AuthService.totp_enroll(db_session, tenant.id, active_user.id)
    assert "otpauth_uri" in result
    assert "qr_base64" in result
    assert "activia-trace" in result["otpauth_uri"]


async def test_totp_enroll_user_not_found_raises(db_session: AsyncSession, tenant: Tenant):
    with pytest.raises(AuthError, match="User not found"):
        await AuthService.totp_enroll(db_session, tenant.id, uuid.uuid4())


# ── TOTP confirm enroll ────────────────────────────────────────────────────────

async def test_totp_confirm_enroll_success(db_session: AsyncSession, tenant: Tenant, active_user: User):
    secret = pyotp.random_base32()
    active_user.totp_pending_secret_enc = _CIPHER.encrypt(secret)
    await db_session.commit()

    code = pyotp.TOTP(secret).now()
    result = await AuthService.totp_confirm_enroll(db_session, tenant.id, active_user.id, code)
    assert result is True

    await db_session.commit()
    await db_session.refresh(active_user)
    assert active_user.totp_enabled is True
    assert active_user.totp_pending_secret_enc is None


async def test_totp_confirm_enroll_no_pending_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    with pytest.raises(AuthError, match="No pending TOTP enrollment"):
        await AuthService.totp_confirm_enroll(db_session, tenant.id, active_user.id, "123456")


async def test_totp_confirm_enroll_invalid_code_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    secret = pyotp.random_base32()
    active_user.totp_pending_secret_enc = _CIPHER.encrypt(secret)
    await db_session.commit()

    with pytest.raises(AuthError, match="Invalid TOTP code"):
        await AuthService.totp_confirm_enroll(db_session, tenant.id, active_user.id, "000000")


# ── TOTP verify gate ───────────────────────────────────────────────────────────

async def test_totp_verify_gate_success(db_session: AsyncSession, tenant: Tenant, totp_user):
    user, secret = totp_user
    partial_token = create_partial_token(str(user.id), str(tenant.id))
    code = pyotp.TOTP(secret).now()

    result = await AuthService.totp_verify_gate(db_session, tenant.id, partial_token, code)
    assert isinstance(result, TokenResponse)
    assert result.access_token
    assert result.refresh_token


async def test_totp_verify_gate_invalid_token_raises(db_session: AsyncSession, tenant: Tenant):
    with pytest.raises(AuthError, match="Invalid partial token"):
        await AuthService.totp_verify_gate(db_session, tenant.id, "not.a.valid.jwt", "123456")


async def test_totp_verify_gate_wrong_scope_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    from app.core.security import create_access_token as _cat

    normal_token = _cat(
        {"sub": str(active_user.id), "tenant_id": str(tenant.id), "roles": []},
        timedelta(minutes=5),
    )
    with pytest.raises(AuthError, match="Invalid token scope"):
        await AuthService.totp_verify_gate(db_session, tenant.id, normal_token, "123456")


async def test_totp_verify_gate_tenant_mismatch_raises(db_session: AsyncSession, tenant: Tenant, totp_user):
    user, _ = totp_user
    partial_token = create_partial_token(str(user.id), str(tenant.id))

    with pytest.raises(AuthError, match="Tenant mismatch"):
        await AuthService.totp_verify_gate(db_session, uuid.uuid4(), partial_token, "123456")


async def test_totp_verify_gate_2fa_not_configured_raises(db_session: AsyncSession, tenant: Tenant, active_user: User):
    partial_token = create_partial_token(str(active_user.id), str(tenant.id))
    with pytest.raises(AuthError, match="2FA not configured"):
        await AuthService.totp_verify_gate(db_session, tenant.id, partial_token, "123456")


async def test_totp_verify_gate_invalid_code_raises(db_session: AsyncSession, tenant: Tenant, totp_user):
    user, _ = totp_user
    partial_token = create_partial_token(str(user.id), str(tenant.id))
    with pytest.raises(AuthError, match="Invalid TOTP code"):
        await AuthService.totp_verify_gate(db_session, tenant.id, partial_token, "000000")
