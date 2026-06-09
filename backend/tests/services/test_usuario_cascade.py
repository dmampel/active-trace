"""Tests de cascada de cierre de asignaciones al desactivar usuario — Strict TDD.

Tasks 4.5, 4.6:
  4.5 - desactivar usuario cierra asignaciones vigentes con hasta=fecha_baja
        y genera audit ASIGNACION_MODIFICAR por cada una.
  4.6 - emite alerta (VACANCIA_GENERADA) a cada responsable_id único;
        si responsable_id is None se omite sin error.
"""
import uuid
import os
from datetime import date, timedelta

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, call

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

import app.models  # noqa: F401


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant_id(db_session) -> uuid.UUID:
    from sqlalchemy import text
    tid = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, created_at, updated_at) VALUES (:id, :name, true, now(), now())"),
        {"id": tid, "name": f"tenant-{tid.hex[:8]}"},
    )
    await db_session.commit()
    return tid


@pytest_asyncio.fixture
async def actor_user(db_session, tenant_id):
    """Actor que realiza la operación (current_user para el service)."""
    from app.models.user import User
    from app.models.estructura import EstadoEntidad
    u = User(
        tenant_id=tenant_id,
        email=f"actor-{uuid.uuid4().hex[:6]}@test.com",
        password_hash="hash",
        estado=EstadoEntidad.activa,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    u.impersonado_id = None  # expected by audit
    return u


@pytest_asyncio.fixture
async def target_user(db_session, tenant_id):
    """Usuario a desactivar."""
    from app.models.user import User
    from app.models.estructura import EstadoEntidad
    u = User(
        tenant_id=tenant_id,
        email=f"target-{uuid.uuid4().hex[:6]}@test.com",
        password_hash="hash",
        estado=EstadoEntidad.activa,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def responsable_user(db_session, tenant_id):
    """Responsable de una asignación."""
    from app.models.user import User
    from app.models.estructura import EstadoEntidad
    u = User(
        tenant_id=tenant_id,
        email=f"resp-{uuid.uuid4().hex[:6]}@test.com",
        password_hash="hash",
        estado=EstadoEntidad.activa,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def vigente_asig(db_session, tenant_id, target_user, responsable_user):
    """Asignación vigente del target_user con responsable."""
    from app.models.asignacion import Asignacion, RolDominio
    asig = Asignacion(
        tenant_id=tenant_id,
        usuario_id=target_user.id,
        rol=RolDominio.PROFESOR,
        desde=date.today() - timedelta(days=30),
        hasta=None,
        responsable_id=responsable_user.id,
        comisiones=[],
    )
    db_session.add(asig)
    await db_session.commit()
    await db_session.refresh(asig)
    return asig


@pytest_asyncio.fixture
async def vigente_asig_sin_responsable(db_session, tenant_id, target_user):
    """Asignación vigente sin responsable_id."""
    from app.models.asignacion import Asignacion, RolDominio
    asig = Asignacion(
        tenant_id=tenant_id,
        usuario_id=target_user.id,
        rol=RolDominio.TUTOR,
        desde=date.today() - timedelta(days=10),
        hasta=None,
        responsable_id=None,
        comisiones=[],
    )
    db_session.add(asig)
    await db_session.commit()
    await db_session.refresh(asig)
    return asig


# ── 4.5 Cascada cierra asignaciones y audita ──────────────────────────────────

@pytest.mark.asyncio
async def test_desactivar_usuario_cierra_asignaciones_vigentes(
    db_session, tenant_id, actor_user, target_user, vigente_asig
):
    """Al desactivar, las asignaciones vigentes reciben hasta=fecha_baja."""
    from app.services.usuario_service import UsuarioService
    from app.models.estructura import EstadoEntidad
    from app.repositories.asignacion_repository import AsignacionRepository

    svc = UsuarioService(db_session, actor_user)
    today = date.today()

    with patch("app.core.audit.record_audit", new=AsyncMock()):
        await svc.update(target_user.id, {"estado": EstadoEntidad.inactiva})

    # La asignación debe tener hasta = fecha_baja (today)
    repo = AsignacionRepository(db_session)
    asig = await repo.get_by_id(vigente_asig.id, tenant_id)
    # get_by_id filtra deleted_at IS NULL pero no hasta — así que la asig
    # sigue existiendo, solo con hasta seteado
    # Need to fetch without the vigente filter — query directly
    from sqlalchemy import select
    from app.models.asignacion import Asignacion
    result = await db_session.execute(
        select(Asignacion).where(Asignacion.id == vigente_asig.id)
    )
    asig_updated = result.scalar_one_or_none()
    assert asig_updated is not None
    assert asig_updated.hasta == today


@pytest.mark.asyncio
async def test_desactivar_usuario_genera_audit_por_cada_asignacion(
    db_session, tenant_id, actor_user, target_user, vigente_asig
):
    """Al desactivar, se genera audit ASIGNACION_MODIFICAR por cada asignación cerrada."""
    from app.services.usuario_service import UsuarioService
    from app.models.estructura import EstadoEntidad
    from app.core.audit import ASIGNACION_MODIFICAR

    svc = UsuarioService(db_session, actor_user)
    audit_calls = []

    async def fake_audit(session, current_user, action, request=None, detail=None, **kwargs):
        audit_calls.append(action)

    with patch("app.services.usuario_service.record_audit", new=fake_audit):
        await svc.update(target_user.id, {"estado": EstadoEntidad.inactiva})

    # Debe haber al menos una llamada con ASIGNACION_MODIFICAR
    assert ASIGNACION_MODIFICAR in audit_calls


# ── 4.6 Alerta a responsable_id; None → sin error ─────────────────────────────

@pytest.mark.asyncio
async def test_desactivar_emite_alerta_a_responsable(
    db_session, tenant_id, actor_user, target_user, vigente_asig, responsable_user
):
    """Al desactivar, se emite VACANCIA_GENERADA al responsable_id único."""
    from app.services.usuario_service import UsuarioService
    from app.models.estructura import EstadoEntidad

    svc = UsuarioService(db_session, actor_user)
    audit_calls = []

    async def fake_audit(session, current_user, action, request=None, detail=None, **kwargs):
        audit_calls.append((action, detail))

    with patch("app.services.usuario_service.record_audit", new=fake_audit):
        await svc.update(target_user.id, {"estado": EstadoEntidad.inactiva})

    vacancia_calls = [c for c in audit_calls if c[0] == "VACANCIA_GENERADA"]
    assert len(vacancia_calls) >= 1
    # El detalle debe mencionar el responsable
    responsable_ids_notified = {c[1]["responsable_id"] for c in vacancia_calls}
    assert str(responsable_user.id) in responsable_ids_notified


@pytest.mark.asyncio
async def test_desactivar_sin_responsable_no_genera_error(
    db_session, tenant_id, actor_user, target_user, vigente_asig_sin_responsable
):
    """Si responsable_id es None, se omite la alerta sin lanzar error."""
    from app.services.usuario_service import UsuarioService
    from app.models.estructura import EstadoEntidad

    svc = UsuarioService(db_session, actor_user)

    with patch("app.core.audit.record_audit", new=AsyncMock()):
        # No debe lanzar excepción
        await svc.update(target_user.id, {"estado": EstadoEntidad.inactiva})


@pytest.mark.asyncio
async def test_desactivar_responsable_unico_una_sola_alerta(
    db_session, tenant_id, actor_user, target_user,
    vigente_asig, responsable_user
):
    """Mismo responsable_id en múltiples asignaciones → una sola alerta."""
    from app.models.asignacion import Asignacion, RolDominio
    from app.services.usuario_service import UsuarioService
    from app.models.estructura import EstadoEntidad

    # Segunda asignación vigente con el mismo responsable
    asig2 = Asignacion(
        tenant_id=tenant_id,
        usuario_id=target_user.id,
        rol=RolDominio.TUTOR,
        desde=date.today() - timedelta(days=5),
        hasta=None,
        responsable_id=responsable_user.id,
        comisiones=[],
    )
    db_session.add(asig2)
    await db_session.commit()

    svc = UsuarioService(db_session, actor_user)
    audit_calls = []

    async def fake_audit(session, current_user, action, request=None, detail=None, **kwargs):
        audit_calls.append((action, detail))

    with patch("app.services.usuario_service.record_audit", new=fake_audit):
        await svc.update(target_user.id, {"estado": EstadoEntidad.inactiva})

    vacancia_calls = [c for c in audit_calls if c[0] == "VACANCIA_GENERADA"]
    # Solo UNA alerta para el mismo responsable
    assert len(vacancia_calls) == 1
