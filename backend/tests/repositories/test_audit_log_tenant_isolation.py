"""Test de aislamiento multi-tenant del audit log."""
import uuid
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.audit_log import AuditLog
from app.core.security import hash_password


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session


def _setup_tenant_with_actor(db, name, email):
    tenant = Tenant(id=uuid.uuid4(), name=name)
    actor = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password("pass"),
        is_active=True,
    )
    db.add_all([tenant, actor])
    db.flush()
    return tenant, actor


def _write_entry(db, tenant_id, actor_id, accion):
    from app.repositories.audit_log_repository import AuditLogRepository
    AuditLogRepository.sync_create_entry(
        db,
        {"id": uuid.uuid4(), "tenant_id": tenant_id, "actor_id": actor_id, "accion": accion},
    )
    db.flush()


def test_audit_log_tenant_isolation(db):
    """10.1 — registro del tenant A no aparece en query del tenant B."""
    tenant_a, actor_a = _setup_tenant_with_actor(db, "Tenant A", "a@test.com")
    tenant_b, actor_b = _setup_tenant_with_actor(db, "Tenant B", "b@test.com")

    _write_entry(db, tenant_a.id, actor_a.id, "ACCION_A")
    _write_entry(db, tenant_b.id, actor_b.id, "ACCION_B")

    entries_a = db.execute(
        select(AuditLog).where(AuditLog.tenant_id == tenant_a.id)
    ).scalars().all()
    entries_b = db.execute(
        select(AuditLog).where(AuditLog.tenant_id == tenant_b.id)
    ).scalars().all()

    assert len(entries_a) == 1
    assert entries_a[0].accion == "ACCION_A"

    assert len(entries_b) == 1
    assert entries_b[0].accion == "ACCION_B"

    # Verificar que los registros NO se cruzan entre tenants
    all_entries_a_ids = {e.tenant_id for e in entries_a}
    assert tenant_b.id not in all_entries_a_ids
