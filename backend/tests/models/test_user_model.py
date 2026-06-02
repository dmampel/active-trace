import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base, UUIDMixin, TenantMixin, TimestampMixin, SoftDeleteMixin
from app.models.user import User, RefreshToken, PasswordResetToken
from app.models.tenant import Tenant


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
    t = Tenant(name=f"Tenant-{uuid.uuid4().hex[:8]}")
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


# ── User model ────────────────────────────────────────────────────────────────

def test_user_inherits_mixins():
    assert issubclass(User, UUIDMixin)
    assert issubclass(User, TimestampMixin)
    assert issubclass(User, SoftDeleteMixin)
    assert issubclass(User, TenantMixin)


def test_user_creates_with_required_fields(session, tenant):
    user = User(
        tenant_id=tenant.id,
        email="test@example.com",
        password_hash="hashed_password",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    assert isinstance(user.id, uuid.UUID)
    assert user.email == "test@example.com"
    assert user.tenant_id == tenant.id
    assert user.totp_enabled is False
    assert user.is_active is True
    assert user.totp_secret_enc is None
    assert user.totp_pending_secret_enc is None
    assert user.deleted_at is None


def test_user_soft_delete(session, tenant):
    from datetime import datetime, timezone
    user = User(
        tenant_id=tenant.id,
        email="delete@example.com",
        password_hash="hashed",
    )
    session.add(user)
    session.commit()

    user.deleted_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(user)
    assert user.deleted_at is not None


# ── RefreshToken model ────────────────────────────────────────────────────────

def test_refresh_token_has_family_id(session, tenant):
    user = User(tenant_id=tenant.id, email="rt@example.com", password_hash="h")
    session.add(user)
    session.commit()

    family = uuid.uuid4()
    from datetime import datetime, timezone, timedelta
    rt = RefreshToken(
        user_id=user.id,
        tenant_id=tenant.id,
        token_hash="abc123hash",
        family_id=family,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add(rt)
    session.commit()
    session.refresh(rt)

    assert rt.family_id == family
    assert rt.revoked_at is None
    assert isinstance(rt.id, uuid.UUID)


def test_refresh_token_can_be_revoked(session, tenant):
    from datetime import datetime, timezone, timedelta
    user = User(tenant_id=tenant.id, email="revoke@example.com", password_hash="h")
    session.add(user)
    session.commit()

    rt = RefreshToken(
        user_id=user.id,
        tenant_id=tenant.id,
        token_hash="revoke_hash",
        family_id=uuid.uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    session.add(rt)
    session.commit()

    rt.revoked_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(rt)
    assert rt.revoked_at is not None


# ── PasswordResetToken model ──────────────────────────────────────────────────

def test_password_reset_token_fields(session, tenant):
    from datetime import datetime, timezone, timedelta
    user = User(tenant_id=tenant.id, email="reset@example.com", password_hash="h")
    session.add(user)
    session.commit()

    prt = PasswordResetToken(
        user_id=user.id,
        tenant_id=tenant.id,
        token_hash="reset_hash_xyz",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    session.add(prt)
    session.commit()
    session.refresh(prt)

    assert prt.used_at is None
    assert isinstance(prt.id, uuid.UUID)
    assert prt.token_hash == "reset_hash_xyz"
