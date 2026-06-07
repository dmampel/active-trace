"""Tests para repositorios de estructura académica.

Strict TDD — usa SQLite in-memory para aislamiento.
"""
import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.estructura import Carrera, Cohorte, Materia, InstanciaDictado, EstadoEntidad


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await e.dispose()


@pytest.fixture
async def db(engine):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
async def tenant(db):
    t = Tenant(id=uuid.uuid4(), name="Tenant Test")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
async def other_tenant(db):
    t = Tenant(id=uuid.uuid4(), name="Other Tenant")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
async def carrera(db, tenant):
    from app.repositories.estructura_repository import CarreraRepository
    repo = CarreraRepository(db)
    return await repo.create(tenant.id, {"codigo": "TUPAD", "nombre": "Tecnicatura"})


@pytest.fixture
async def materia(db, tenant):
    from app.repositories.estructura_repository import MateriaRepository
    repo = MateriaRepository(db)
    return await repo.create(tenant.id, {"codigo": "PROG_I", "nombre": "Programación I"})


@pytest.fixture
async def cohorte(db, tenant, carrera):
    from app.repositories.estructura_repository import CohorteRepository
    repo = CohorteRepository(db)
    return await repo.create(tenant.id, {
        "carrera_id": carrera.id, "nombre": "MAR-2026",
        "anio": 2026, "vig_desde": date(2026, 3, 1),
    })


# ── 8.1 CarreraRepository — tenant isolation ──────────────────────────────────

@pytest.mark.asyncio
async def test_carrera_list_active_tenant_isolation(db, tenant, other_tenant):
    from app.repositories.estructura_repository import CarreraRepository
    repo = CarreraRepository(db)
    await repo.create(tenant.id, {"codigo": "C1", "nombre": "Carrera 1"})
    await repo.create(other_tenant.id, {"codigo": "C2", "nombre": "Carrera 2"})

    result = await repo.list_active(tenant.id)
    assert len(result) == 1
    assert result[0].codigo == "C1"


@pytest.mark.asyncio
async def test_carrera_list_excludes_deleted(db, tenant):
    from app.repositories.estructura_repository import CarreraRepository
    repo = CarreraRepository(db)
    c = await repo.create(tenant.id, {"codigo": "DEL", "nombre": "A borrar"})
    await repo.soft_delete(c.id, tenant.id)

    result = await repo.list_active(tenant.id)
    assert all(r.codigo != "DEL" for r in result)


# ── 8.2 CohorteRepository — filtro por carrera ────────────────────────────────

@pytest.mark.asyncio
async def test_cohorte_list_active_filters_by_carrera(db, tenant, carrera):
    from app.repositories.estructura_repository import CarreraRepository, CohorteRepository
    repo_c = CarreraRepository(db)
    repo_coh = CohorteRepository(db)

    other = await repo_c.create(tenant.id, {"codigo": "OTR", "nombre": "Otra carrera"})
    await repo_coh.create(tenant.id, {"carrera_id": carrera.id, "nombre": "MAR-2026", "anio": 2026, "vig_desde": date(2026, 3, 1)})
    await repo_coh.create(tenant.id, {"carrera_id": other.id, "nombre": "AGO-2026", "anio": 2026, "vig_desde": date(2026, 8, 1)})

    result = await repo_coh.list_active(tenant.id, carrera_id=carrera.id)
    assert len(result) == 1
    assert result[0].nombre == "MAR-2026"


# ── 8.3 soft_delete en CarreraRepository ─────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(db, tenant):
    from app.repositories.estructura_repository import CarreraRepository
    repo = CarreraRepository(db)
    c = await repo.create(tenant.id, {"codigo": "SD", "nombre": "Soft Delete Test"})

    await repo.soft_delete(c.id, tenant.id)
    await db.refresh(c)
    assert c.deleted_at is not None

    visible = await repo.list_active(tenant.id)
    assert all(r.id != c.id for r in visible)


# ── 8.4 InstanciaDictadoRepository — filtro por cohorte ──────────────────────

@pytest.mark.asyncio
async def test_instancia_list_active_filters_by_cohorte(db, tenant, materia, cohorte):
    from app.repositories.estructura_repository import CohorteRepository, InstanciaDictadoRepository
    repo_coh = CohorteRepository(db)
    repo_ins = InstanciaDictadoRepository(db)

    other_cohorte = await repo_coh.create(tenant.id, {
        "carrera_id": cohorte.carrera_id, "nombre": "AGO-2026",
        "anio": 2026, "vig_desde": date(2026, 8, 1),
    })
    await repo_ins.create(tenant.id, {"materia_id": materia.id, "cohorte_id": cohorte.id, "nombre": "Prog Python", "periodo": "2026-1"})
    await repo_ins.create(tenant.id, {"materia_id": materia.id, "cohorte_id": other_cohorte.id, "nombre": "Prog Java", "periodo": "2026-2"})

    result = await repo_ins.list_active(tenant.id, cohorte_id=cohorte.id)
    assert len(result) == 1
    assert result[0].nombre == "Prog Python"
