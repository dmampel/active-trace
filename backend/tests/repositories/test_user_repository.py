import uuid
from datetime import datetime, timezone, timedelta

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.user_repository import UserRepository


@pytest_asyncio.fixture
async def tenant_a(db_session: AsyncSession):
    t = Tenant(name=f"TenantA-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession):
    t = Tenant(name=f"TenantB-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def user_a(db_session: AsyncSession, tenant_a):
    u = User(tenant_id=tenant_a.id, email="a@example.com", password_hash="h")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def user_b(db_session: AsyncSession, tenant_b):
    u = User(tenant_id=tenant_b.id, email="b@example.com", password_hash="h")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


# ── get_by_email ──────────────────────────────────────────────────────────────

async def test_get_by_email_found(db_session: AsyncSession, tenant_a, user_a):
    result = await UserRepository.get_by_email(db_session, tenant_a.id, "a@example.com")
    assert result is not None
    assert result.id == user_a.id


async def test_get_by_email_case_insensitive(db_session: AsyncSession, tenant_a, user_a):
    # user_a fixture creates the user — the variable is needed even if body doesn't reference it
    result = await UserRepository.get_by_email(db_session, tenant_a.id, "A@EXAMPLE.COM")
    assert result is not None


async def test_get_by_email_not_found_wrong_tenant(db_session: AsyncSession, tenant_b, user_a):
    result = await UserRepository.get_by_email(db_session, tenant_b.id, "a@example.com")
    assert result is None


async def test_get_by_email_not_found_wrong_email(db_session: AsyncSession, tenant_a):
    result = await UserRepository.get_by_email(db_session, tenant_a.id, "noexist@example.com")
    assert result is None


# ── get_by_id ─────────────────────────────────────────────────────────────────

async def test_get_by_id_found(db_session: AsyncSession, tenant_a, user_a):
    result = await UserRepository.get_by_id(db_session, tenant_a.id, user_a.id)
    assert result is not None
    assert result.email == "a@example.com"


async def test_get_by_id_not_found_wrong_tenant(db_session: AsyncSession, tenant_b, user_a):
    result = await UserRepository.get_by_id(db_session, tenant_b.id, user_a.id)
    assert result is None


# ── RefreshToken operations ───────────────────────────────────────────────────

async def test_create_and_get_refresh_token(db_session: AsyncSession, tenant_a, user_a):
    family = uuid.uuid4()
    exp = datetime.now(timezone.utc) + timedelta(days=7)
    await UserRepository.create_refresh_token(
        db_session, user_a.id, tenant_a.id, "hash_abc_" + uuid.uuid4().hex, family, exp
    )
    await db_session.commit()

    token_hash = "hash_abc_" + uuid.uuid4().hex
    await UserRepository.create_refresh_token(db_session, user_a.id, tenant_a.id, token_hash, family, exp)
    await db_session.commit()

    fetched = await UserRepository.get_refresh_token_by_hash(db_session, token_hash, tenant_a.id)
    assert fetched is not None
    assert fetched.family_id == family
    assert fetched.revoked_at is None


async def test_get_refresh_token_wrong_tenant_returns_none(db_session: AsyncSession, tenant_a, tenant_b, user_a):
    family = uuid.uuid4()
    exp = datetime.now(timezone.utc) + timedelta(days=7)
    token_hash = "hash_tenant_iso_" + uuid.uuid4().hex
    await UserRepository.create_refresh_token(db_session, user_a.id, tenant_a.id, token_hash, family, exp)
    await db_session.commit()

    result = await UserRepository.get_refresh_token_by_hash(db_session, token_hash, tenant_b.id)
    assert result is None


async def test_revoke_refresh_family_only_revokes_same_family(db_session: AsyncSession, tenant_a, user_a):
    family_x = uuid.uuid4()
    family_y = uuid.uuid4()
    exp = datetime.now(timezone.utc) + timedelta(days=7)
    prefix = uuid.uuid4().hex

    hash_x1 = f"x1_{prefix}"
    hash_x2 = f"x2_{prefix}"
    hash_y1 = f"y1_{prefix}"

    await UserRepository.create_refresh_token(db_session, user_a.id, tenant_a.id, hash_x1, family_x, exp)
    await UserRepository.create_refresh_token(db_session, user_a.id, tenant_a.id, hash_x2, family_x, exp)
    await UserRepository.create_refresh_token(db_session, user_a.id, tenant_a.id, hash_y1, family_y, exp)
    await db_session.commit()

    await UserRepository.revoke_refresh_family(db_session, family_x)
    await db_session.commit()

    rt_x1 = await UserRepository.get_refresh_token_by_hash(db_session, hash_x1, tenant_a.id)
    rt_x2 = await UserRepository.get_refresh_token_by_hash(db_session, hash_x2, tenant_a.id)
    rt_y1 = await UserRepository.get_refresh_token_by_hash(db_session, hash_y1, tenant_a.id)

    assert rt_x1.revoked_at is not None
    assert rt_x2.revoked_at is not None
    assert rt_y1.revoked_at is None


# ── PasswordResetToken operations ─────────────────────────────────────────────

async def test_create_and_get_reset_token(db_session: AsyncSession, tenant_a, user_a):
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    token_hash = "reset_" + uuid.uuid4().hex
    await UserRepository.create_reset_token(db_session, user_a.id, tenant_a.id, token_hash, exp)
    await db_session.commit()

    fetched = await UserRepository.get_reset_token_by_hash(db_session, token_hash, tenant_a.id)
    assert fetched is not None
    assert fetched.used_at is None


async def test_get_reset_token_wrong_tenant_returns_none(db_session: AsyncSession, tenant_a, tenant_b, user_a):
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    token_hash = "reset_iso_" + uuid.uuid4().hex
    await UserRepository.create_reset_token(db_session, user_a.id, tenant_a.id, token_hash, exp)
    await db_session.commit()

    result = await UserRepository.get_reset_token_by_hash(db_session, token_hash, tenant_b.id)
    assert result is None


async def test_get_reset_token_returns_none_for_unknown_hash(db_session: AsyncSession, tenant_a):
    result = await UserRepository.get_reset_token_by_hash(db_session, "nonexistent_hash", tenant_a.id)
    assert result is None


async def test_mark_reset_token_used(db_session: AsyncSession, tenant_a, user_a):
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    token_hash = "reset_used_" + uuid.uuid4().hex
    prt = await UserRepository.create_reset_token(db_session, user_a.id, tenant_a.id, token_hash, exp)
    await db_session.commit()

    await UserRepository.mark_reset_token_used(db_session, prt.id)
    await db_session.commit()

    fetched = await UserRepository.get_reset_token_by_hash(db_session, token_hash, tenant_a.id)
    assert fetched.used_at is not None
