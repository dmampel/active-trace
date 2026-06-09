"""Tests del repositorio de usuarios.

Strict TDD:
  3.1 - tenant isolation en create y get_by_id
  3.2 - unicidad (tenant_id, email)
  3.4 - soft_delete setea deleted_at; no aparece en list_active
"""
import uuid
import os

import pytest
import pytest_asyncio
from sqlalchemy import text

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

# Registrar todos los modelos para que create_all (conftest) cree asignacion + estructura
import app.models  # noqa: F401


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant_id(db_session) -> uuid.UUID:
    tid = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, created_at, updated_at) VALUES (:id, :name, true, now(), now())"),
        {"id": tid, "name": f"tenant-{tid.hex[:8]}"},
    )
    await db_session.commit()
    return tid


@pytest_asyncio.fixture
async def tenant2_id(db_session) -> uuid.UUID:
    tid = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, created_at, updated_at) VALUES (:id, :name, true, now(), now())"),
        {"id": tid, "name": f"tenant2-{tid.hex[:8]}"},
    )
    await db_session.commit()
    return tid


def _user_data(email: str = None) -> dict:
    return {
        "email": email or f"user-{uuid.uuid4().hex[:8]}@example.com",
        "password_hash": "hash",
    }


# ── 3.1 Tenant isolation ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_assigns_tenant_id(db_session, tenant_id):
    from app.repositories.usuario_repository import UsuarioRepository
    repo = UsuarioRepository(db_session)
    user = await repo.create(tenant_id, _user_data())
    assert user.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_get_by_id_scoped_to_tenant(db_session, tenant_id, tenant2_id):
    from app.repositories.usuario_repository import UsuarioRepository
    repo = UsuarioRepository(db_session)
    user = await repo.create(tenant_id, _user_data())
    found = await repo.get_by_id(user.id, tenant_id)
    assert found is not None
    assert found.id == user.id
    not_found = await repo.get_by_id(user.id, tenant2_id)
    assert not_found is None


# ── 3.2 Unicidad (tenant_id, email) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_email_same_tenant_raises(db_session, tenant_id):
    from sqlalchemy.exc import IntegrityError
    from app.repositories.usuario_repository import UsuarioRepository
    repo = UsuarioRepository(db_session)
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    await repo.create(tenant_id, _user_data(email))
    with pytest.raises(IntegrityError):
        await repo.create(tenant_id, _user_data(email))


@pytest.mark.asyncio
async def test_same_email_different_tenant_allowed(db_session, tenant_id, tenant2_id):
    from app.repositories.usuario_repository import UsuarioRepository
    repo = UsuarioRepository(db_session)
    email = f"shared-{uuid.uuid4().hex[:8]}@example.com"
    u1 = await repo.create(tenant_id, _user_data(email))
    u2 = await repo.create(tenant2_id, _user_data(email))
    assert u1.id != u2.id


# ── 3.4 Soft delete ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(db_session, tenant_id):
    from app.repositories.usuario_repository import UsuarioRepository
    repo = UsuarioRepository(db_session)
    user = await repo.create(tenant_id, _user_data())
    assert user.deleted_at is None
    result = await repo.soft_delete(user.id, tenant_id)
    assert result is True
    fetched = await repo.get_by_id(user.id, tenant_id)
    assert fetched is None  # soft deleted no aparece en get_by_id


@pytest.mark.asyncio
async def test_soft_deleted_user_not_in_list_active(db_session, tenant_id):
    from app.repositories.usuario_repository import UsuarioRepository
    repo = UsuarioRepository(db_session)
    user = await repo.create(tenant_id, _user_data())
    await repo.soft_delete(user.id, tenant_id)
    active = await repo.list_active(tenant_id)
    ids = [u.id for u in active]
    assert user.id not in ids
