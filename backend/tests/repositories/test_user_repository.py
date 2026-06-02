import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User, RefreshToken, PasswordResetToken
from app.repositories.user_repository import UserRepository


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
def tenant_a(session):
    t = Tenant(name=f"TenantA-{uuid.uuid4().hex[:6]}")
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@pytest.fixture
def tenant_b(session):
    t = Tenant(name=f"TenantB-{uuid.uuid4().hex[:6]}")
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@pytest.fixture
def user_a(session, tenant_a):
    u = User(tenant_id=tenant_a.id, email="a@example.com", password_hash="h")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


@pytest.fixture
def user_b(session, tenant_b):
    u = User(tenant_id=tenant_b.id, email="b@example.com", password_hash="h")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


# ── get_by_email ──────────────────────────────────────────────────────────────

def test_get_by_email_found(session, tenant_a, user_a):
    result = UserRepository.get_by_email(session, tenant_a.id, "a@example.com")
    assert result is not None
    assert result.id == user_a.id


def test_get_by_email_not_found_wrong_tenant(session, tenant_b, user_a):
    # user_a belongs to tenant_a — must NOT be visible from tenant_b
    result = UserRepository.get_by_email(session, tenant_b.id, "a@example.com")
    assert result is None


def test_get_by_email_not_found_wrong_email(session, tenant_a):
    result = UserRepository.get_by_email(session, tenant_a.id, "noexist@example.com")
    assert result is None


# ── get_by_id ─────────────────────────────────────────────────────────────────

def test_get_by_id_found(session, tenant_a, user_a):
    result = UserRepository.get_by_id(session, tenant_a.id, user_a.id)
    assert result is not None
    assert result.email == "a@example.com"


def test_get_by_id_not_found_wrong_tenant(session, tenant_b, user_a):
    result = UserRepository.get_by_id(session, tenant_b.id, user_a.id)
    assert result is None


# ── RefreshToken operations ───────────────────────────────────────────────────

def test_create_and_get_refresh_token(session, tenant_a, user_a):
    family = uuid.uuid4()
    exp = datetime.now(timezone.utc) + timedelta(days=7)
    rt = UserRepository.create_refresh_token(
        session, user_a.id, tenant_a.id, "hash_abc", family, exp
    )
    session.commit()

    fetched = UserRepository.get_refresh_token_by_hash(session, "hash_abc")
    assert fetched is not None
    assert fetched.family_id == family
    assert fetched.revoked_at is None


def test_revoke_refresh_family_only_revokes_same_family(session, tenant_a, user_a):
    family_x = uuid.uuid4()
    family_y = uuid.uuid4()
    exp = datetime.now(timezone.utc) + timedelta(days=7)

    rt_x1 = UserRepository.create_refresh_token(session, user_a.id, tenant_a.id, "hash_x1", family_x, exp)
    rt_x2 = UserRepository.create_refresh_token(session, user_a.id, tenant_a.id, "hash_x2", family_x, exp)
    rt_y1 = UserRepository.create_refresh_token(session, user_a.id, tenant_a.id, "hash_y1", family_y, exp)
    session.commit()

    UserRepository.revoke_refresh_family(session, family_x)
    session.commit()

    session.refresh(rt_x1)
    session.refresh(rt_x2)
    session.refresh(rt_y1)

    assert rt_x1.revoked_at is not None
    assert rt_x2.revoked_at is not None
    assert rt_y1.revoked_at is None  # different family — untouched


# ── PasswordResetToken operations ─────────────────────────────────────────────

def test_create_and_get_reset_token(session, tenant_a, user_a):
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    UserRepository.create_reset_token(session, user_a.id, tenant_a.id, "reset_hash_1", exp)
    session.commit()

    fetched = UserRepository.get_reset_token_by_hash(session, "reset_hash_1")
    assert fetched is not None
    assert fetched.used_at is None


def test_get_reset_token_returns_none_for_unknown_hash(session):
    result = UserRepository.get_reset_token_by_hash(session, "nonexistent_hash")
    assert result is None


def test_mark_reset_token_used(session, tenant_a, user_a):
    exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    rt = UserRepository.create_reset_token(session, user_a.id, tenant_a.id, "reset_hash_used", exp)
    session.commit()

    UserRepository.mark_reset_token_used(session, rt.id)
    session.commit()
    session.refresh(rt)

    assert rt.used_at is not None
