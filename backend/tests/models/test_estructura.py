"""Tests para modelos y migración de estructura académica.

Strict TDD — safety net: 92/93 tests GREEN (1 pre-existing DB connection failure).
"""
import uuid
from datetime import date
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.base import Base
from app.models.tenant import Tenant


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sync_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db(async_engine):
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
async def tenant(db):
    t = Tenant(id=uuid.uuid4(), name="Test Tenant")
    db.add(t)
    await db.commit()
    return t


# ── 7.1 Migración — import y tabla ────────────────────────────────────────────

def test_estructura_models_importable():
    from app.models.estructura import Carrera, Cohorte, Materia, InstanciaDictado
    assert Carrera.__tablename__ == "carrera"
    assert Cohorte.__tablename__ == "cohorte"
    assert Materia.__tablename__ == "materia"
    assert InstanciaDictado.__tablename__ == "instancia_dictado"


def test_estructura_tables_created_in_sqlite(sync_engine):
    with sync_engine.connect() as conn:
        for table in ("carrera", "cohorte", "materia", "instancia_dictado"):
            result = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"))
            assert result.fetchone() is not None, f"Tabla {table} no encontrada"


# ── 7.2 Crear Carrera ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_carrera_persists(db, tenant):
    from app.models.estructura import Carrera, EstadoEntidad
    c = Carrera(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        codigo="TUPAD",
        nombre="Tecnicatura Universitaria en Programación",
        estado=EstadoEntidad.activa,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    assert c.codigo == "TUPAD"
    assert c.estado == EstadoEntidad.activa
    assert c.deleted_at is None


@pytest.mark.asyncio
async def test_create_materia_persists(db, tenant):
    from app.models.estructura import Materia, EstadoEntidad
    m = Materia(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        codigo="PROG_I",
        nombre="Programación I",
        estado=EstadoEntidad.activa,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    assert m.codigo == "PROG_I"


# ── 7.3 Constraint único Carrera ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_carrera_unique_codigo_per_tenant(db, tenant):
    from app.models.estructura import Carrera, EstadoEntidad
    c1 = Carrera(id=uuid.uuid4(), tenant_id=tenant.id, codigo="DUP", nombre="Carrera A", estado=EstadoEntidad.activa)
    c2 = Carrera(id=uuid.uuid4(), tenant_id=tenant.id, codigo="DUP", nombre="Carrera B", estado=EstadoEntidad.activa)
    db.add(c1)
    await db.commit()
    db.add(c2)
    with pytest.raises(IntegrityError):
        await db.commit()


# ── 7.4 Constraint único InstanciaDictado ─────────────────────────────────────

@pytest.mark.asyncio
async def test_instancia_unique_constraint(db, tenant):
    from app.models.estructura import Carrera, Cohorte, Materia, InstanciaDictado, EstadoEntidad
    carrera = Carrera(id=uuid.uuid4(), tenant_id=tenant.id, codigo="CAR1", nombre="Carrera 1", estado=EstadoEntidad.activa)
    materia = Materia(id=uuid.uuid4(), tenant_id=tenant.id, codigo="MAT1", nombre="Materia 1", estado=EstadoEntidad.activa)
    cohorte = Cohorte(
        id=uuid.uuid4(), tenant_id=tenant.id, carrera_id=carrera.id,
        nombre="MAR-2026", anio=2026, vig_desde=date(2026, 3, 1), estado=EstadoEntidad.activa,
    )
    db.add_all([carrera, materia, cohorte])
    await db.commit()

    i1 = InstanciaDictado(
        id=uuid.uuid4(), tenant_id=tenant.id,
        materia_id=materia.id, cohorte_id=cohorte.id,
        nombre="Prog Python", periodo="2026-1", estado=EstadoEntidad.activa,
    )
    i2 = InstanciaDictado(
        id=uuid.uuid4(), tenant_id=tenant.id,
        materia_id=materia.id, cohorte_id=cohorte.id,
        nombre="Prog Python Dup", periodo="2026-1", estado=EstadoEntidad.activa,
    )
    db.add(i1)
    await db.commit()
    db.add(i2)
    with pytest.raises(IntegrityError):
        await db.commit()
