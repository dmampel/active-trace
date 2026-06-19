"""Tests de integración para TareaRepository y ComentarioTareaRepository (C-16).

Usa DB real PostgreSQL (activia-test, puerto 5433).
Cubre: create, get_by_id (tenant isolation), list_mis_tareas, list_all, update_estado,
comentarios (create + list en orden cronológico).

Safety net: 549 passed + 30 errors (pre-existing test_usuario_cascade.py) antes de estos tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tarea import EstadoTarea
from app.repositories.tarea_repository import ComentarioTareaRepository, TareaRepository
from app.schemas.tarea import TareaCreate


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant_a(db_session: AsyncSession):
    from app.models.tenant import Tenant
    t = Tenant(name=f"TenantTareaA-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession):
    from app.models.tenant import Tenant
    t = Tenant(name=f"TenantTareaB-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def user_a(db_session: AsyncSession, tenant_a):
    from app.models.user import User
    u = User(
        tenant_id=tenant_a.id,
        email=f"user_a_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="hashed",
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def user_b(db_session: AsyncSession, tenant_a):
    from app.models.user import User
    u = User(
        tenant_id=tenant_a.id,
        email=f"user_b_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="hashed",
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def user_other_tenant(db_session: AsyncSession, tenant_b):
    from app.models.user import User
    u = User(
        tenant_id=tenant_b.id,
        email=f"user_other_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="hashed",
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def tarea_pendiente(db_session: AsyncSession, tenant_a, user_a, user_b):
    """Tarea en estado pendiente, asignada de user_b a user_a."""
    repo = TareaRepository(db_session)
    data = TareaCreate(
        asignado_a=user_a.id,
        descripcion="Tarea de prueba",
    )
    t = await repo.create(tenant_a.id, user_b.id, data)
    await db_session.commit()
    return t


# ── Task 6.2: create persiste estado=pendiente y tenant_id correcto ───────────


async def test_create_persists_estado_pendiente(db_session: AsyncSession, tenant_a, user_a, user_b):
    """RED→GREEN: create debe retornar tarea con estado=pendiente y tenant_id correcto."""
    repo = TareaRepository(db_session)
    data = TareaCreate(asignado_a=user_a.id, descripcion="Mi primera tarea")

    tarea = await repo.create(tenant_a.id, user_b.id, data)
    await db_session.commit()

    assert tarea.id is not None
    assert tarea.estado == EstadoTarea.pendiente
    assert tarea.tenant_id == tenant_a.id
    assert tarea.asignado_a == user_a.id
    assert tarea.asignado_por == user_b.id
    assert tarea.descripcion == "Mi primera tarea"


async def test_create_with_optional_fields(db_session: AsyncSession, tenant_a, user_a, user_b):
    """TRIANGULATE: create con campos opcionales."""
    repo = TareaRepository(db_session)
    contexto_id = uuid.uuid4()
    data = TareaCreate(
        asignado_a=user_a.id,
        descripcion="Tarea con contexto",
        contexto_id=contexto_id,
    )

    tarea = await repo.create(tenant_a.id, user_b.id, data)
    await db_session.commit()

    assert tarea.contexto_id == contexto_id
    assert tarea.materia_id is None


# ── Task 6.3: get_by_id con tarea de otro tenant retorna None ─────────────────


async def test_get_by_id_returns_none_for_wrong_tenant(
    db_session: AsyncSession, tarea_pendiente, tenant_b
):
    """RED→GREEN: get_by_id aislamiento cross-tenant."""
    repo = TareaRepository(db_session)
    result = await repo.get_by_id(tenant_b.id, tarea_pendiente.id)
    assert result is None


async def test_get_by_id_found_correct_tenant(
    db_session: AsyncSession, tarea_pendiente, tenant_a
):
    """TRIANGULATE: get_by_id con tenant correcto devuelve la tarea."""
    repo = TareaRepository(db_session)
    result = await repo.get_by_id(tenant_a.id, tarea_pendiente.id)
    assert result is not None
    assert result.id == tarea_pendiente.id


# ── Task 6.4: list_mis_tareas filtra por asignado_a y estado ─────────────────


async def test_list_mis_tareas_filtra_por_asignado_a(
    db_session: AsyncSession, tenant_a, user_a, user_b
):
    """RED→GREEN: list_mis_tareas devuelve solo las tareas del usuario."""
    repo = TareaRepository(db_session)

    # Crear 2 tareas para user_a
    await repo.create(tenant_a.id, user_b.id, TareaCreate(asignado_a=user_a.id, descripcion="T1"))
    await repo.create(tenant_a.id, user_b.id, TareaCreate(asignado_a=user_a.id, descripcion="T2"))
    # Crear 1 tarea para user_b (no debe aparecer)
    await repo.create(tenant_a.id, user_a.id, TareaCreate(asignado_a=user_b.id, descripcion="T3"))
    await db_session.commit()

    tareas = await repo.list_mis_tareas(tenant_a.id, user_a.id)
    assert len(tareas) >= 2
    assert all(t.asignado_a == user_a.id for t in tareas)


async def test_list_mis_tareas_filtra_por_estado(
    db_session: AsyncSession, tenant_a, user_a, user_b
):
    """TRIANGULATE: list_mis_tareas con filtro de estado."""
    repo = TareaRepository(db_session)

    t1 = await repo.create(
        tenant_a.id, user_b.id, TareaCreate(asignado_a=user_a.id, descripcion="Pendiente")
    )
    await repo.update_estado(tenant_a.id, t1.id, EstadoTarea.en_progreso)
    await repo.create(
        tenant_a.id, user_b.id, TareaCreate(asignado_a=user_a.id, descripcion="También pendiente")
    )
    await db_session.commit()

    pendientes = await repo.list_mis_tareas(tenant_a.id, user_a.id, EstadoTarea.pendiente)
    en_progreso = await repo.list_mis_tareas(tenant_a.id, user_a.id, EstadoTarea.en_progreso)

    assert all(t.estado == EstadoTarea.pendiente for t in pendientes)
    assert all(t.estado == EstadoTarea.en_progreso for t in en_progreso)


# ── Task 6.5: list_all retorna paginación correcta ───────────────────────────


async def test_list_all_paginacion(db_session: AsyncSession, tenant_a, user_a, user_b):
    """RED→GREEN: list_all retorna paginación con total correcto."""
    repo = TareaRepository(db_session)

    for i in range(5):
        await repo.create(
            tenant_a.id, user_b.id,
            TareaCreate(asignado_a=user_a.id, descripcion=f"Tarea pag {i}"),
        )
    await db_session.commit()

    items_p1, total = await repo.list_all(tenant_a.id, {}, page=1, size=3)
    assert total >= 5
    assert len(items_p1) == 3

    items_p2, total2 = await repo.list_all(tenant_a.id, {}, page=2, size=3)
    assert total2 == total


async def test_list_all_filtra_por_estado(db_session: AsyncSession, tenant_a, user_a, user_b):
    """TRIANGULATE: list_all con filtro combinado de estado y asignado_a."""
    repo = TareaRepository(db_session)

    t1 = await repo.create(
        tenant_a.id, user_b.id, TareaCreate(asignado_a=user_a.id, descripcion="F1")
    )
    await repo.update_estado(tenant_a.id, t1.id, EstadoTarea.en_progreso)
    await repo.create(
        tenant_a.id, user_b.id, TareaCreate(asignado_a=user_a.id, descripcion="F2")
    )
    await db_session.commit()

    items, total = await repo.list_all(
        tenant_a.id,
        {"estado": EstadoTarea.en_progreso, "asignado_a": user_a.id},
        page=1,
        size=50,
    )
    assert all(t.estado == EstadoTarea.en_progreso for t in items)
    assert all(t.asignado_a == user_a.id for t in items)


# ── Task 6.6: update_estado persiste nuevo estado ────────────────────────────


async def test_update_estado_persiste(db_session: AsyncSession, tarea_pendiente, tenant_a):
    """RED→GREEN: update_estado cambia el estado en la DB."""
    repo = TareaRepository(db_session)
    assert tarea_pendiente.estado == EstadoTarea.pendiente

    actualizada = await repo.update_estado(tenant_a.id, tarea_pendiente.id, EstadoTarea.en_progreso)
    await db_session.commit()

    assert actualizada is not None
    assert actualizada.estado == EstadoTarea.en_progreso


async def test_update_estado_wrong_tenant_retorna_none(
    db_session: AsyncSession, tarea_pendiente, tenant_b
):
    """TRIANGULATE: update_estado con tenant incorrecto retorna None."""
    repo = TareaRepository(db_session)
    result = await repo.update_estado(tenant_b.id, tarea_pendiente.id, EstadoTarea.en_progreso)
    assert result is None


# ── Task 6.7: comentarios create + list en orden cronológico ──────────────────


async def test_comentario_create_y_list_cronologico(
    db_session: AsyncSession, tarea_pendiente, tenant_a, user_a, user_b
):
    """RED→GREEN: create comentario y list_comentarios en orden asc."""
    repo = ComentarioTareaRepository(db_session)

    t0 = datetime.now(timezone.utc)
    c1 = await repo.create(tenant_a.id, tarea_pendiente.id, user_a.id, "Primer comentario")
    t1 = datetime.now(timezone.utc)
    c2 = await repo.create(tenant_a.id, tarea_pendiente.id, user_b.id, "Segundo comentario")
    await db_session.commit()

    comentarios = await repo.list_comentarios(tenant_a.id, tarea_pendiente.id)
    assert len(comentarios) >= 2

    ids_en_orden = [c.id for c in comentarios]
    assert ids_en_orden.index(c1.id) < ids_en_orden.index(c2.id)


async def test_comentario_list_tenant_isolation(
    db_session: AsyncSession, tarea_pendiente, tenant_a, tenant_b, user_a
):
    """TRIANGULATE: list_comentarios con tenant incorrecto retorna lista vacía."""
    repo = ComentarioTareaRepository(db_session)

    await repo.create(tenant_a.id, tarea_pendiente.id, user_a.id, "Comentario real")
    await db_session.commit()

    # Consultar con tenant_b: la tarea_id existe pero pertenece a tenant_a
    comentarios = await repo.list_comentarios(tenant_b.id, tarea_pendiente.id)
    assert len(comentarios) == 0
