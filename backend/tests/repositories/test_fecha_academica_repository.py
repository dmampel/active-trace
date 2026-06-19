"""Tests de integración para FechaAcademicaRepository (C-17, Tareas 8.1–8.7).

Usa DB real PostgreSQL (activia-test, puerto 5433).
Cubre: create (tenant correcto), create duplicado (unicidad), get_by_id (tenant
isolation), list con filtros y orden cronológico, update (409 unicidad), soft_delete.

Safety net: 582 passed, 2 skipped, 19 pre-existing errors antes de estos tests.
"""

from __future__ import annotations

import uuid
from datetime import date
import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluacion import FechaAcademica, TipoFechaAcademica
from app.repositories.fecha_academica_repository import FechaAcademicaRepository


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant_a(db_session: AsyncSession):
    from app.models.tenant import Tenant
    t = Tenant(name=f"TenantFechaA-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession):
    from app.models.tenant import Tenant
    t = Tenant(name=f"TenantFechaB-{uuid.uuid4().hex[:6]}")
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
        nombre="Materia Fecha Test",
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
        nombre="Carrera Fecha Test",
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


def _make_fecha(
    tenant_id: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    *,
    tipo: TipoFechaAcademica = TipoFechaAcademica.Parcial,
    numero: int = 1,
    periodo: str = "2026-1",
    fecha: str = "2026-05-10",
    titulo: str = "Parcial 1",
) -> FechaAcademica:
    return FechaAcademica(
        tenant_id=tenant_id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=tipo,
        numero=numero,
        periodo=periodo,
        fecha=fecha,
        titulo=titulo,
    )


# ── Task 8.1: create persiste FechaAcademica con tenant correcto ──────────────


async def test_create_persiste_con_tenant_correcto(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """RED→GREEN: create retorna FechaAcademica con tenant_id y campos correctos."""
    repo = FechaAcademicaRepository(db_session)
    fecha = _make_fecha(tenant_a.id, materia.id, cohorte.id)

    creada = await repo.create(fecha)
    await db_session.commit()

    assert creada.id is not None
    assert creada.tenant_id == tenant_a.id
    assert creada.materia_id == materia.id
    assert creada.cohorte_id == cohorte.id
    assert creada.tipo == TipoFechaAcademica.Parcial
    assert creada.numero == 1
    assert creada.periodo == "2026-1"
    assert creada.fecha == "2026-05-10"
    assert creada.titulo == "Parcial 1"


async def test_create_tipos_distintos(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """TRIANGULATE: create de TP en el mismo período es válido (contexto diferente)."""
    repo = FechaAcademicaRepository(db_session)
    fecha = _make_fecha(
        tenant_a.id, materia.id, cohorte.id,
        tipo=TipoFechaAcademica.TP,
        numero=1,
        titulo="TP 1",
    )
    creada = await repo.create(fecha)
    await db_session.commit()
    assert creada.tipo == TipoFechaAcademica.TP


# ── Task 8.2: create duplicado lanza IntegrityError ──────────────────────────


async def test_create_duplicado_lanza_integrity_error(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """RED→GREEN: create con mismo (tipo, numero, periodo) lanza IntegrityError."""
    repo = FechaAcademicaRepository(db_session)

    await repo.create(_make_fecha(tenant_a.id, materia.id, cohorte.id))
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await repo.create(
            _make_fecha(tenant_a.id, materia.id, cohorte.id, titulo="Duplicado")
        )


# ── Task 8.3: get_by_id con otro tenant retorna None ─────────────────────────


async def test_get_by_id_otro_tenant_retorna_none(
    db_session: AsyncSession, tenant_a, tenant_b, materia, cohorte
):
    """RED→GREEN: get_by_id con tenant incorrecto retorna None (aislamiento)."""
    repo = FechaAcademicaRepository(db_session)
    creada = await repo.create(_make_fecha(tenant_a.id, materia.id, cohorte.id))
    await db_session.commit()

    result = await repo.get_by_id(tenant_b.id, creada.id)
    assert result is None


async def test_get_by_id_tenant_correcto_retorna_fecha(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """TRIANGULATE: get_by_id con tenant correcto retorna la fecha."""
    repo = FechaAcademicaRepository(db_session)
    creada = await repo.create(_make_fecha(tenant_a.id, materia.id, cohorte.id))
    await db_session.commit()

    result = await repo.get_by_id(tenant_a.id, creada.id)
    assert result is not None
    assert result.id == creada.id


# ── Task 8.4: list filtra por materia_id, cohorte_id y periodo ───────────────


async def test_list_filtra_por_periodo(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """RED→GREEN: list con filtro de periodo devuelve solo las fechas del período."""
    repo = FechaAcademicaRepository(db_session)

    await repo.create(_make_fecha(tenant_a.id, materia.id, cohorte.id, periodo="2026-1"))
    await db_session.commit()
    await repo.create(
        _make_fecha(
            tenant_a.id, materia.id, cohorte.id,
            tipo=TipoFechaAcademica.TP, numero=1, periodo="2026-2", titulo="TP 2"
        )
    )
    await db_session.commit()

    result_1 = await repo.list(tenant_a.id, materia_id=materia.id, cohorte_id=cohorte.id, periodo="2026-1")
    result_2 = await repo.list(tenant_a.id, materia_id=materia.id, cohorte_id=cohorte.id, periodo="2026-2")

    assert all(f.periodo == "2026-1" for f in result_1)
    assert all(f.periodo == "2026-2" for f in result_2)


async def test_list_filtra_por_materia_y_cohorte(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """TRIANGULATE: list sin filtro de periodo devuelve todas las fechas del contexto."""
    repo = FechaAcademicaRepository(db_session)

    # Crear 2 fechas para materia/cohorte
    await repo.create(_make_fecha(tenant_a.id, materia.id, cohorte.id, numero=1, titulo="P1"))
    await db_session.commit()
    await repo.create(
        _make_fecha(
            tenant_a.id, materia.id, cohorte.id,
            tipo=TipoFechaAcademica.TP, numero=1, titulo="TP1"
        )
    )
    await db_session.commit()

    result = await repo.list(tenant_a.id, materia_id=materia.id, cohorte_id=cohorte.id)
    ids = [f.id for f in result]
    assert len(ids) >= 2


# ── Task 8.5: list devuelve resultados ordenados por fecha ascendente ─────────


async def test_list_orden_fecha_ascendente(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """RED→GREEN: list devuelve resultados ordenados por fecha ascendente."""
    repo = FechaAcademicaRepository(db_session)

    # Crear en orden invertido de fecha
    await repo.create(
        _make_fecha(tenant_a.id, materia.id, cohorte.id, numero=2, fecha="2026-06-20", titulo="Parcial 2")
    )
    await db_session.commit()
    await repo.create(
        _make_fecha(tenant_a.id, materia.id, cohorte.id, numero=1, fecha="2026-04-10", titulo="Parcial 1")
    )
    await db_session.commit()

    result = await repo.list(tenant_a.id, materia_id=materia.id, cohorte_id=cohorte.id)
    fechas = [f.fecha for f in result]
    assert fechas == sorted(fechas)


# ── Task 8.6: update genera 409 si viola unicidad ────────────────────────────


async def test_update_viola_unicidad_lanza_integrity_error(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """RED→GREEN: update que viola UniqueConstraint lanza IntegrityError."""
    repo = FechaAcademicaRepository(db_session)

    # Crear dos fechas con diferente numero
    _ = await repo.create(_make_fecha(tenant_a.id, materia.id, cohorte.id, numero=1, titulo="P1"))
    await db_session.commit()
    f2 = await repo.create(
        _make_fecha(tenant_a.id, materia.id, cohorte.id, numero=2, titulo="P2")
    )
    await db_session.commit()

    # Intentar cambiar f2 para que tenga el mismo contexto que f1
    with pytest.raises(IntegrityError):
        await repo.update(f2.id, tenant_a.id, numero=1)


async def test_update_campo_no_unicidad_funciona(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """TRIANGULATE: update de titulo (sin afectar unicidad) funciona."""
    repo = FechaAcademicaRepository(db_session)
    creada = await repo.create(_make_fecha(tenant_a.id, materia.id, cohorte.id))
    await db_session.commit()

    actualizada = await repo.update(creada.id, tenant_a.id, titulo="Parcial 1 (Actualizado)")
    await db_session.commit()

    assert actualizada is not None
    assert actualizada.titulo == "Parcial 1 (Actualizado)"


# ── Task 8.7: soft_delete → consulta posterior retorna None ──────────────────


async def test_soft_delete_oculta_fecha(
    db_session: AsyncSession, tenant_a, materia, cohorte
):
    """RED→GREEN: soft_delete → get_by_id posterior retorna None."""
    repo = FechaAcademicaRepository(db_session)
    creada = await repo.create(_make_fecha(tenant_a.id, materia.id, cohorte.id))
    await db_session.commit()

    deleted = await repo.soft_delete(creada.id, tenant_a.id)
    await db_session.commit()

    assert deleted is True
    result = await repo.get_by_id(tenant_a.id, creada.id)
    assert result is None


async def test_soft_delete_inexistente_retorna_false(
    db_session: AsyncSession, tenant_a
):
    """TRIANGULATE: soft_delete de ID inexistente retorna False."""
    repo = FechaAcademicaRepository(db_session)
    deleted = await repo.soft_delete(uuid.uuid4(), tenant_a.id)
    assert deleted is False
