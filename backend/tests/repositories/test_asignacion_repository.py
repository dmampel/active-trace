"""Tests del repositorio de asignaciones — Strict TDD.

Tasks 6.1, 6.3, 6.5:
  6.1 - derivación estado_vigencia
  6.3 - tenant scope + validación FK del mismo tenant
  6.5 - histórico conservado, soft_delete no borra físicamente
"""
import uuid
import os
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

import app.models  # noqa: F401 — registrar todos los modelos


# ── Fixtures ───────────────────────────────────────────────────────────────────

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


@pytest_asyncio.fixture
async def usuario_id(db_session, tenant_id) -> uuid.UUID:
    from app.models.user import User
    from app.models.estructura import EstadoEntidad
    uid = uuid.uuid4()
    user = User(
        id=uid,
        tenant_id=tenant_id,
        email=f"user-{uid.hex[:8]}@test.com",
        password_hash="hash",
        estado=EstadoEntidad.activa,
    )
    db_session.add(user)
    await db_session.commit()
    return uid


@pytest_asyncio.fixture
async def usuario2_id(db_session, tenant2_id) -> uuid.UUID:
    from app.models.user import User
    from app.models.estructura import EstadoEntidad
    uid = uuid.uuid4()
    user = User(
        id=uid,
        tenant_id=tenant2_id,
        email=f"user2-{uid.hex[:8]}@test.com",
        password_hash="hash",
        estado=EstadoEntidad.activa,
    )
    db_session.add(user)
    await db_session.commit()
    return uid


def _asig_data(usuario_id: uuid.UUID, desde: date = None, hasta: date = None,
               responsable_id: uuid.UUID = None) -> dict:
    return {
        "usuario_id": usuario_id,
        "rol": "PROFESOR",
        "desde": desde or date.today(),
        "hasta": hasta,
        "responsable_id": responsable_id,
        "comisiones": [],
    }


# ── 6.1 Derivación estado_vigencia ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vigencia_vigente_sin_hasta(db_session, tenant_id, usuario_id):
    """desde<=hoy y hasta IS NULL ⇒ Vigente."""
    from app.repositories.asignacion_repository import AsignacionRepository
    repo = AsignacionRepository(db_session)
    asig = await repo.create(tenant_id, _asig_data(usuario_id))
    assert asig.hasta is None
    vigencia = repo.derive_estado_vigencia(asig)
    assert vigencia == "Vigente"


@pytest.mark.asyncio
async def test_vigencia_vigente_con_hasta_futuro(db_session, tenant_id, usuario_id):
    """desde<=hoy y hasta en el futuro ⇒ Vigente."""
    from app.repositories.asignacion_repository import AsignacionRepository
    repo = AsignacionRepository(db_session)
    hasta = date.today() + timedelta(days=30)
    asig = await repo.create(tenant_id, _asig_data(usuario_id, hasta=hasta))
    vigencia = repo.derive_estado_vigencia(asig)
    assert vigencia == "Vigente"


@pytest.mark.asyncio
async def test_vigencia_vencida_hasta_pasado(db_session, tenant_id, usuario_id):
    """hasta en el pasado ⇒ Vencida."""
    from app.repositories.asignacion_repository import AsignacionRepository
    repo = AsignacionRepository(db_session)
    hasta = date.today() - timedelta(days=1)
    asig = await repo.create(tenant_id, _asig_data(usuario_id, desde=date.today() - timedelta(days=10), hasta=hasta))
    vigencia = repo.derive_estado_vigencia(asig)
    assert vigencia == "Vencida"


# ── 6.3 Tenant scope ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_id_scoped_to_tenant(db_session, tenant_id, tenant2_id, usuario_id, usuario2_id):
    """get_by_id devuelve la asignación solo para el tenant correcto."""
    from app.repositories.asignacion_repository import AsignacionRepository
    repo = AsignacionRepository(db_session)
    asig = await repo.create(tenant_id, _asig_data(usuario_id))
    # mismo tenant → encontrado
    found = await repo.get_by_id(asig.id, tenant_id)
    assert found is not None
    # otro tenant → no encontrado
    not_found = await repo.get_by_id(asig.id, tenant2_id)
    assert not_found is None


@pytest.mark.asyncio
async def test_list_vigentes_scoped_to_tenant(db_session, tenant_id, tenant2_id, usuario_id, usuario2_id):
    """list_vigentes no devuelve asignaciones de otros tenants."""
    from app.repositories.asignacion_repository import AsignacionRepository
    repo = AsignacionRepository(db_session)
    # asig en tenant1
    asig1 = await repo.create(tenant_id, _asig_data(usuario_id))
    # asig en tenant2
    asig2 = await repo.create(tenant2_id, _asig_data(usuario2_id))

    list_t1 = await repo.list_vigentes(tenant_id)
    ids_t1 = [a.id for a in list_t1]
    assert asig1.id in ids_t1
    assert asig2.id not in ids_t1


# ── 6.5 Histórico y soft delete ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_historico_vencida_consultable(db_session, tenant_id, usuario_id):
    """Asignación con hasta en el pasado: se conserva y es consultable."""
    from app.repositories.asignacion_repository import AsignacionRepository
    repo = AsignacionRepository(db_session)
    hasta = date.today() - timedelta(days=5)
    asig = await repo.create(tenant_id, _asig_data(usuario_id, desde=date.today() - timedelta(days=10), hasta=hasta))
    found = await repo.get_by_id(asig.id, tenant_id)
    assert found is not None
    assert found.hasta == hasta


@pytest.mark.asyncio
async def test_soft_delete_no_borra_fisicamente(db_session, tenant_id, usuario_id):
    """soft_delete setea deleted_at, el registro NO se elimina físicamente."""
    from app.repositories.asignacion_repository import AsignacionRepository
    from sqlalchemy import text as sa_text
    repo = AsignacionRepository(db_session)
    asig = await repo.create(tenant_id, _asig_data(usuario_id))
    await repo.soft_delete(asig.id, tenant_id)
    # get_by_id no lo devuelve (filtrado por deleted_at IS NULL)
    not_found = await repo.get_by_id(asig.id, tenant_id)
    assert not_found is None
    # pero existe físicamente en la DB
    row = await db_session.execute(
        sa_text("SELECT deleted_at FROM asignacion WHERE id = :id"),
        {"id": asig.id},
    )
    result = row.fetchone()
    assert result is not None
    assert result[0] is not None  # deleted_at seteado


@pytest.mark.asyncio
async def test_list_with_filters_by_usuario(db_session, tenant_id, usuario_id):
    """list con filtro usuario_id devuelve solo sus asignaciones."""
    from app.repositories.asignacion_repository import AsignacionRepository
    repo = AsignacionRepository(db_session)
    asig = await repo.create(tenant_id, _asig_data(usuario_id))
    results = await repo.list(tenant_id, usuario_id=usuario_id)
    ids = [a.id for a in results]
    assert asig.id in ids


@pytest.mark.asyncio
async def test_update_asignacion(db_session, tenant_id, usuario_id):
    """update modifica campos correctamente."""
    from app.repositories.asignacion_repository import AsignacionRepository
    repo = AsignacionRepository(db_session)
    asig = await repo.create(tenant_id, _asig_data(usuario_id))
    nueva_hasta = date.today() + timedelta(days=30)
    updated = await repo.update(asig.id, tenant_id, {"hasta": nueva_hasta})
    assert updated is not None
    assert updated.hasta == nueva_hasta
