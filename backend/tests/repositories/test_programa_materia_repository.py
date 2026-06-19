"""Tests de integración para ProgramaMateriaRepository (C-17, Tareas 7.1–7.7).

Usa DB real PostgreSQL (activia-test, puerto 5433).
Cubre: create (tenant correcto), create duplicado (409 unicidad),
get_by_id (tenant isolation), get_by_context, update (solo campos enviados),
soft_delete (consulta posterior retorna None).

Safety net: 582 passed, 2 skipped, 19 pre-existing errors antes de estos tests.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.programa_materia_repository import ProgramaMateriaRepository
from app.schemas.programa_materia import ProgramaMateriaCreate, ProgramaMateriaUpdate


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant_a(db_session: AsyncSession):
    from app.models.tenant import Tenant
    t = Tenant(name=f"TenantProgA-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession):
    from app.models.tenant import Tenant
    t = Tenant(name=f"TenantProgB-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def materia(db_session: AsyncSession, tenant_a):
    from app.models.estructura import EstadoEntidad, Materia
    m = Materia(
        tenant_id=tenant_a.id,
        codigo=f"MAT-{uuid.uuid4().hex[:6]}",
        nombre="Materia Test",
        estado=EstadoEntidad.activa,
    )
    db_session.add(m)
    await db_session.commit()
    await db_session.refresh(m)
    return m


@pytest_asyncio.fixture
async def carrera(db_session: AsyncSession, tenant_a):
    from app.models.estructura import Carrera, EstadoEntidad
    c = Carrera(
        tenant_id=tenant_a.id,
        codigo=f"CAR-{uuid.uuid4().hex[:6]}",
        nombre="Carrera Test",
        estado=EstadoEntidad.activa,
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


@pytest_asyncio.fixture
async def cohorte(db_session: AsyncSession, tenant_a, carrera):
    from app.models.estructura import Cohorte, EstadoEntidad
    c = Cohorte(
        tenant_id=tenant_a.id,
        carrera_id=carrera.id,
        anio=2026,
        nombre="2026",
        vig_desde=date(2026, 3, 1),
        estado=EstadoEntidad.activa,
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


@pytest_asyncio.fixture
async def programa_existente(db_session: AsyncSession, tenant_a, materia, carrera, cohorte):
    """Un ProgramaMateria ya persistido en tenant_a."""
    repo = ProgramaMateriaRepository(db_session)
    data = ProgramaMateriaCreate(
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        titulo="Programa Base",
        referencia_archivo="https://drive.example.com/prog-base.pdf",
    )
    prog = await repo.create(tenant_a.id, data)
    await db_session.commit()
    return prog


# ── Task 7.2: create persiste con tenant correcto ────────────────────────────


async def test_create_persiste_con_tenant_correcto(
    db_session: AsyncSession, tenant_a, materia, carrera, cohorte
):
    """RED→GREEN: create retorna ProgramaMateria con tenant_id y campos correctos."""
    repo = ProgramaMateriaRepository(db_session)
    data = ProgramaMateriaCreate(
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        titulo="Programa 2026",
        referencia_archivo="https://storage.example.com/prog.pdf",
    )

    prog = await repo.create(tenant_a.id, data)
    await db_session.commit()

    assert prog.id is not None
    assert prog.tenant_id == tenant_a.id
    assert prog.materia_id == materia.id
    assert prog.carrera_id == carrera.id
    assert prog.cohorte_id == cohorte.id
    assert prog.titulo == "Programa 2026"
    assert prog.referencia_archivo == "https://storage.example.com/prog.pdf"
    assert prog.cargado_at is not None  # set porque referencia_archivo no es None


async def test_create_sin_referencia_archivo(
    db_session: AsyncSession, tenant_a, materia, carrera, cohorte
):
    """TRIANGULATE: create sin referencia_archivo — cargado_at debe ser None."""
    repo = ProgramaMateriaRepository(db_session)
    data = ProgramaMateriaCreate(
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        titulo="Programa sin archivo",
    )

    prog = await repo.create(tenant_a.id, data)
    await db_session.commit()

    assert prog.referencia_archivo is None
    assert prog.cargado_at is None


# ── Task 7.3: create duplicado lanza IntegrityError ──────────────────────────


async def test_create_duplicado_lanza_integrity_error(
    db_session: AsyncSession, tenant_a, materia, carrera, cohorte, programa_existente  # noqa: ARG001
):
    """RED→GREEN: create con contexto duplicado lanza IntegrityError."""
    repo = ProgramaMateriaRepository(db_session)
    data = ProgramaMateriaCreate(
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        titulo="Programa Duplicado",
    )

    with pytest.raises(IntegrityError):
        await repo.create(tenant_a.id, data)


# ── Task 7.4: get_by_id con otro tenant retorna None ─────────────────────────


async def test_get_by_id_otro_tenant_retorna_none(
    db_session: AsyncSession, tenant_b, programa_existente
):
    """RED→GREEN: get_by_id con tenant incorrecto retorna None (aislamiento)."""
    repo = ProgramaMateriaRepository(db_session)
    result = await repo.get_by_id(tenant_b.id, programa_existente.id)
    assert result is None


async def test_get_by_id_tenant_correcto_retorna_programa(
    db_session: AsyncSession, tenant_a, programa_existente
):
    """TRIANGULATE: get_by_id con tenant correcto retorna el programa."""
    repo = ProgramaMateriaRepository(db_session)
    result = await repo.get_by_id(tenant_a.id, programa_existente.id)
    assert result is not None
    assert result.id == programa_existente.id


# ── Task 7.5: get_by_context retorna el programa correcto ────────────────────


async def test_get_by_context_retorna_programa(
    db_session: AsyncSession, tenant_a, materia, carrera, cohorte, programa_existente
):
    """RED→GREEN: get_by_context retorna el programa para el contexto correcto."""
    repo = ProgramaMateriaRepository(db_session)
    result = await repo.get_by_context(tenant_a.id, materia.id, carrera.id, cohorte.id)
    assert result is not None
    assert result.id == programa_existente.id
    assert result.titulo == "Programa Base"


async def test_get_by_context_inexistente_retorna_none(
    db_session: AsyncSession, tenant_a, materia, carrera, cohorte
):
    """TRIANGULATE: get_by_context sin programa previo retorna None."""
    repo = ProgramaMateriaRepository(db_session)
    result = await repo.get_by_context(tenant_a.id, materia.id, carrera.id, cohorte.id)
    assert result is None


# ── Task 7.6: update modifica solo los campos enviados ───────────────────────


async def test_update_modifica_titulo(
    db_session: AsyncSession, tenant_a, programa_existente
):
    """RED→GREEN: update modifica solo los campos presentes en data."""
    repo = ProgramaMateriaRepository(db_session)
    data = ProgramaMateriaUpdate(titulo="Nuevo Título 2026")

    actualizado = await repo.update(tenant_a.id, programa_existente.id, data)
    await db_session.commit()

    assert actualizado is not None
    assert actualizado.titulo == "Nuevo Título 2026"
    # referencia_archivo no cambia
    assert actualizado.referencia_archivo == programa_existente.referencia_archivo


async def test_update_modifica_referencia_archivo(
    db_session: AsyncSession, tenant_a, programa_existente
):
    """TRIANGULATE: update modifica referencia_archivo y actualiza cargado_at."""
    repo = ProgramaMateriaRepository(db_session)
    data = ProgramaMateriaUpdate(referencia_archivo="https://nuevo.example.com/prog-v2.pdf")

    cargado_at_original = programa_existente.cargado_at
    actualizado = await repo.update(tenant_a.id, programa_existente.id, data)
    await db_session.commit()

    assert actualizado is not None
    assert actualizado.referencia_archivo == "https://nuevo.example.com/prog-v2.pdf"
    assert actualizado.cargado_at is not None
    # cargado_at debe ser más reciente o igual (puede ser igual si muy rápido)
    assert actualizado.cargado_at >= cargado_at_original


# ── Task 7.7: soft_delete → consulta posterior retorna None ──────────────────


async def test_soft_delete_oculta_programa(
    db_session: AsyncSession, tenant_a, programa_existente
):
    """RED→GREEN: soft_delete → get_by_id posterior retorna None."""
    repo = ProgramaMateriaRepository(db_session)

    deleted = await repo.soft_delete(tenant_a.id, programa_existente.id)
    await db_session.commit()

    assert deleted is True
    result = await repo.get_by_id(tenant_a.id, programa_existente.id)
    assert result is None


async def test_soft_delete_inexistente_retorna_false(
    db_session: AsyncSession, tenant_a
):
    """TRIANGULATE: soft_delete de ID inexistente retorna False."""
    repo = ProgramaMateriaRepository(db_session)
    deleted = await repo.soft_delete(tenant_a.id, uuid.uuid4())
    assert deleted is False
