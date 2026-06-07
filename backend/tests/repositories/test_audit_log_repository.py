"""Tests para AuditLogRepository — append-only enforcement."""
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository
from app.core.security import hash_password


@pytest.fixture
def sync_engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def sync_session(sync_engine):
    with Session(sync_engine) as session:
        yield session


@pytest.fixture
def tenant_and_actor(sync_session):
    tenant = Tenant(id=uuid.uuid4(), name="Test Tenant")
    actor = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="actor@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    sync_session.add_all([tenant, actor])
    sync_session.flush()
    return tenant, actor


@pytest.fixture
async def async_engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def async_session(async_engine):
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session


# ── Async repository — append-only overrides ─────────────────────────────────

@pytest.mark.asyncio
async def test_update_raises_not_implemented(async_session):
    """8.4 — update() debe lanzar NotImplementedError."""
    repo = AuditLogRepository(async_session)
    with pytest.raises(NotImplementedError, match="append-only"):
        await repo.update(uuid.uuid4())


@pytest.mark.asyncio
async def test_delete_raises_not_implemented(async_session):
    """8.5 — delete() debe lanzar NotImplementedError."""
    repo = AuditLogRepository(async_session)
    with pytest.raises(NotImplementedError, match="append-only"):
        await repo.delete(uuid.uuid4())


# ── Sync helper — record_audit_sync ──────────────────────────────────────────

def _make_current_user(tenant_id, user_id, impersonado_id=None):
    from app.core.dependencies import CurrentUser
    return CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        roles=[],
        impersonado_id=impersonado_id,
    )


def test_record_audit_creates_entry(sync_session, tenant_and_actor):
    """8.1 — record_audit_sync crea registro con campos correctos."""
    from app.core.audit import record_audit_sync, CALIFICACIONES_IMPORTAR

    tenant, actor = tenant_and_actor
    current_user = _make_current_user(tenant.id, actor.id)

    record_audit_sync(
        sync_session,
        current_user,
        CALIFICACIONES_IMPORTAR,
        request=None,
        detail={"archivo": "padron.xlsx"},
        rows_affected=42,
    )
    sync_session.flush()

    entry = sync_session.query(AuditLog).filter_by(actor_id=actor.id).first()
    assert entry is not None
    assert entry.tenant_id == tenant.id
    assert entry.actor_id == actor.id
    assert entry.accion == CALIFICACIONES_IMPORTAR
    assert entry.filas_afectadas == 42
    assert entry.detalle == {"archivo": "padron.xlsx"}
    assert entry.impersonado_id is None


def test_record_audit_with_impersonation(sync_session, tenant_and_actor):
    """8.2 — record_audit con impersonado_id: actor_id=actor_real, impersonado_id=target."""
    from app.core.audit import record_audit_sync, PADRON_CARGAR

    tenant, actor = tenant_and_actor
    target_id = uuid.uuid4()
    current_user = _make_current_user(tenant.id, actor.id, impersonado_id=target_id)

    record_audit_sync(sync_session, current_user, PADRON_CARGAR)

    entry = sync_session.query(AuditLog).filter_by(actor_id=actor.id).first()
    assert entry.actor_id == actor.id
    assert entry.impersonado_id == target_id


def test_record_audit_without_impersonation(sync_session, tenant_and_actor):
    """8.3 — sin impersonación, impersonado_id es None."""
    from app.core.audit import record_audit_sync, COMUNICACION_ENVIAR

    tenant, actor = tenant_and_actor
    current_user = _make_current_user(tenant.id, actor.id)

    record_audit_sync(sync_session, current_user, COMUNICACION_ENVIAR)

    entry = sync_session.query(AuditLog).filter_by(actor_id=actor.id).first()
    assert entry.impersonado_id is None


def test_sync_create_entry_persists(sync_session, tenant_and_actor):
    """AuditLogRepository.sync_create_entry escribe un registro persistente."""
    tenant, actor = tenant_and_actor

    entry = AuditLogRepository.sync_create_entry(
        sync_session,
        {
            "id": uuid.uuid4(),
            "tenant_id": tenant.id,
            "actor_id": actor.id,
            "accion": "TEST_ACTION",
        },
    )
    sync_session.flush()

    fetched = sync_session.get(AuditLog, entry.id)
    assert fetched is not None
    assert fetched.accion == "TEST_ACTION"
