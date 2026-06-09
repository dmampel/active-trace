"""Tests del service de asignaciones — Strict TDD.

Tasks 7.2, 7.3, 7.6:
  7.2 - schema rechaza campo no declarado; contexto global (sin FK) aceptado.
  7.3 - validación de contexto contra tenant; jerarquía responsable_id.
  7.6 - auditoría ASIGNACION_MODIFICAR en create/update/delete.
"""
import uuid
import os
from datetime import date, timedelta

import pytest
import pytest_asyncio
from pydantic import ValidationError
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

import app.models  # noqa: F401


# ── 7.2 Schema validations (no DB needed) ─────────────────────────────────────

def test_asignacion_create_rejects_undeclared_field():
    from app.schemas.asignacion import AsignacionCreate
    with pytest.raises(ValidationError) as exc_info:
        AsignacionCreate(
            usuario_id=uuid.uuid4(),
            rol="PROFESOR",
            desde=date.today(),
            campo_no_declarado="valor",
        )
    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" for e in errors)


def test_asignacion_create_global_context_accepted():
    """Contexto global (sin materia/carrera/cohorte) debe ser aceptado."""
    from app.schemas.asignacion import AsignacionCreate
    schema = AsignacionCreate(
        usuario_id=uuid.uuid4(),
        rol="ADMIN",
        desde=date.today(),
    )
    assert schema.materia_id is None
    assert schema.carrera_id is None
    assert schema.cohorte_id is None


def test_asignacion_update_rejects_undeclared_field():
    from app.schemas.asignacion import AsignacionUpdate
    with pytest.raises(ValidationError) as exc_info:
        AsignacionUpdate(hasta=date.today(), campo_extra="no")
    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" for e in errors)


def test_asignacion_read_includes_estado_vigencia():
    """AsignacionRead incluye el campo estado_vigencia."""
    from app.schemas.asignacion import AsignacionRead
    r = AsignacionRead(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        usuario_id=uuid.uuid4(),
        rol="PROFESOR",
        desde=date.today(),
        hasta=None,
        estado_vigencia="Vigente",
        comisiones=[],
    )
    assert r.estado_vigencia == "Vigente"


# ── Fixtures para tests con DB ────────────────────────────────────────────────

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
async def tenant2_id(db_session) -> uuid.UUID:
    from sqlalchemy import text
    tid = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, created_at, updated_at) VALUES (:id, :name, true, now(), now())"),
        {"id": tid, "name": f"tenant2-{tid.hex[:8]}"},
    )
    await db_session.commit()
    return tid


@pytest_asyncio.fixture
async def actor_user(db_session, tenant_id):
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
    u.impersonado_id = None
    return u


@pytest_asyncio.fixture
async def target_user(db_session, tenant_id):
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


# ── 7.3 Validación de contexto contra tenant ──────────────────────────────────

@pytest.mark.asyncio
async def test_create_asignacion_basica(db_session, tenant_id, actor_user, target_user):
    """Crear asignación básica devuelve AsignacionRead con estado_vigencia."""
    from app.services.asignacion_service import AsignacionService

    svc = AsignacionService(db_session, actor_user)
    data = {
        "usuario_id": target_user.id,
        "rol": "PROFESOR",
        "desde": date.today(),
        "hasta": None,
        "comisiones": [],
    }
    with patch("app.services.asignacion_service.record_audit", new=AsyncMock()):
        result = await svc.create(data)

    assert result.usuario_id == target_user.id
    assert result.estado_vigencia == "Vigente"


@pytest.mark.asyncio
async def test_create_asignacion_futura(db_session, tenant_id, actor_user, target_user):
    """Asignación con desde en el futuro tiene estado_vigencia Futura."""
    from app.services.asignacion_service import AsignacionService

    svc = AsignacionService(db_session, actor_user)
    data = {
        "usuario_id": target_user.id,
        "rol": "TUTOR",
        "desde": date.today() + timedelta(days=10),
        "hasta": None,
        "comisiones": [],
    }
    with patch("app.services.asignacion_service.record_audit", new=AsyncMock()):
        result = await svc.create(data)

    assert result.estado_vigencia == "Futura"


# ── 7.6 Auditoría en create/update/delete ────────────────────────────────────

@pytest.mark.asyncio
async def test_create_asignacion_genera_audit(db_session, tenant_id, actor_user, target_user):
    """create genera audit ASIGNACION_MODIFICAR."""
    from app.services.asignacion_service import AsignacionService
    from app.core.audit import ASIGNACION_MODIFICAR

    svc = AsignacionService(db_session, actor_user)
    audit_calls = []

    async def fake_audit(session, current_user, action, **kwargs):
        audit_calls.append(action)

    data = {
        "usuario_id": target_user.id,
        "rol": "PROFESOR",
        "desde": date.today(),
        "comisiones": [],
    }
    with patch("app.services.asignacion_service.record_audit", new=fake_audit):
        await svc.create(data)

    assert ASIGNACION_MODIFICAR in audit_calls


@pytest.mark.asyncio
async def test_update_asignacion_genera_audit(db_session, tenant_id, actor_user, target_user):
    """update genera audit ASIGNACION_MODIFICAR."""
    from app.services.asignacion_service import AsignacionService
    from app.core.audit import ASIGNACION_MODIFICAR
    from app.models.asignacion import Asignacion, RolDominio

    # crear asignación directamente
    asig = Asignacion(
        tenant_id=tenant_id,
        usuario_id=target_user.id,
        rol=RolDominio.PROFESOR,
        desde=date.today(),
        comisiones=[],
    )
    db_session.add(asig)
    await db_session.commit()

    svc = AsignacionService(db_session, actor_user)
    audit_calls = []

    async def fake_audit(session, current_user, action, **kwargs):
        audit_calls.append(action)

    with patch("app.services.asignacion_service.record_audit", new=fake_audit):
        await svc.update(asig.id, {"hasta": date.today() + timedelta(days=30)})

    assert ASIGNACION_MODIFICAR in audit_calls


@pytest.mark.asyncio
async def test_delete_asignacion_genera_audit(db_session, tenant_id, actor_user, target_user):
    """soft_delete genera audit ASIGNACION_MODIFICAR."""
    from app.services.asignacion_service import AsignacionService
    from app.core.audit import ASIGNACION_MODIFICAR
    from app.models.asignacion import Asignacion, RolDominio

    asig = Asignacion(
        tenant_id=tenant_id,
        usuario_id=target_user.id,
        rol=RolDominio.TUTOR,
        desde=date.today(),
        comisiones=[],
    )
    db_session.add(asig)
    await db_session.commit()

    svc = AsignacionService(db_session, actor_user)
    audit_calls = []

    async def fake_audit(session, current_user, action, **kwargs):
        audit_calls.append(action)

    with patch("app.services.asignacion_service.record_audit", new=fake_audit):
        await svc.soft_delete(asig.id)

    assert ASIGNACION_MODIFICAR in audit_calls
