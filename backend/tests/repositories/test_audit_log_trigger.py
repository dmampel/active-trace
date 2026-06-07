"""Test de trigger DB: audit_log es inmutable a nivel PostgreSQL.

Requiere PostgreSQL real — se saltea automáticamente si no hay conexión disponible.
"""
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.audit_log import AuditLog
from app.core.security import hash_password


PG_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/activia_trace_test"


@pytest_asyncio.fixture(scope="module")
async def pg_engine():
    """Engine async contra PostgreSQL real. Se saltea si no conecta."""
    engine = create_async_engine(PG_URL, poolclass=NullPool, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("PostgreSQL no disponible — levantá docker-compose")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Crear función y trigger de protección (idempotente)
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION audit_log_immutable()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE are not permitted';
            END;
            $$ LANGUAGE plpgsql;
        """))
        await conn.execute(text("""
            DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log;
        """))
        await conn.execute(text("""
            CREATE TRIGGER audit_log_no_update_delete
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
        """))

    yield engine

    async with engine.begin() as conn:
        await conn.execute(text("DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log;"))
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def pg_session(pg_engine):
    async with AsyncSession(pg_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def audit_entry(pg_session):
    """Crea un tenant, actor y una entrada de audit_log real en PostgreSQL."""
    tenant = Tenant(id=uuid.uuid4(), name="Trigger Test Tenant")
    pg_session.add(tenant)
    await pg_session.flush()

    actor = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"trigger-{uuid.uuid4()}@test.com",
        password_hash=hash_password("pass"),
        is_active=True,
    )
    pg_session.add(actor)
    await pg_session.flush()

    entry = AuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        actor_id=actor.id,
        accion="TEST_TRIGGER",
    )
    pg_session.add(entry)
    await pg_session.flush()
    return entry


@pytest.mark.asyncio
async def test_trigger_blocks_update(pg_session, audit_entry):
    """8.6a — trigger bloquea UPDATE directo en audit_log."""
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError, match="append-only"):
        await pg_session.execute(
            text("UPDATE audit_log SET accion = 'HACKED' WHERE id = :id"),
            {"id": str(audit_entry.id)},
        )
        await pg_session.flush()


@pytest.mark.asyncio
async def test_trigger_blocks_delete(pg_session, audit_entry):
    """8.6b — trigger bloquea DELETE directo en audit_log."""
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError, match="append-only"):
        await pg_session.execute(
            text("DELETE FROM audit_log WHERE id = :id"),
            {"id": str(audit_entry.id)},
        )
        await pg_session.flush()
