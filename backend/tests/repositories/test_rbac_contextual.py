"""Tests de resolución RBAC con asignaciones contextuales — Strict TDD.

Tasks 8.1, 8.2, 8.4:
  8.1 - Asignación contextual vigente con rol PROFESOR → incluye permisos del rol.
  8.2 - Asignación contextual vencida (hasta en pasado) → NO contribuye permisos.
  8.4 - Revocación (soft delete) de asignación → quita permiso en siguiente consulta.
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

import app.models  # noqa: F401


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant_id(db_session) -> uuid.UUID:
    tid = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, created_at, updated_at) VALUES (:id, :name, true, now(), now())"),
        {"id": tid, "name": f"tenant-rbac-{tid.hex[:8]}"},
    )
    await db_session.commit()
    return tid


@pytest_asyncio.fixture
async def test_user(db_session, tenant_id) -> uuid.UUID:
    """Usuario sin rol global asignado."""
    from app.models.user import User
    from app.models.estructura import EstadoEntidad
    uid = uuid.uuid4()
    user = User(
        id=uid,
        tenant_id=tenant_id,
        email=f"rbac-test-{uid.hex[:8]}@test.com",
        password_hash="hash",
        estado=EstadoEntidad.activa,
    )
    db_session.add(user)
    await db_session.commit()
    return uid


@pytest_asyncio.fixture
async def profesor_rol_id(db_session) -> uuid.UUID:
    """ID del rol PROFESOR en el catálogo."""
    result = await db_session.execute(text("SELECT id FROM rol WHERE nombre = 'PROFESOR'"))
    row = result.fetchone()
    if row is None:
        pytest.skip("Rol PROFESOR no encontrado — migraciones no aplicadas")
    return row[0]


async def _get_perms_for_profesor(db_session, tenant_id):
    """Permisos que debería tener el rol PROFESOR según el catálogo."""
    result = await db_session.execute(
        text("""
            SELECT p.nombre FROM permiso p
            JOIN rol_permiso rp ON rp.permiso_id = p.id
            JOIN rol r ON r.id = rp.rol_id
            WHERE r.nombre = 'PROFESOR'
        """)
    )
    return {row[0] for row in result.fetchall()}


# ── 8.1 Asignación vigente → permisos del rol ─────────────────────────────────

@pytest.mark.asyncio
async def test_asignacion_vigente_agrega_permisos(db_session, tenant_id, test_user, profesor_rol_id):
    """Asignación vigente con rol PROFESOR incluye sus permisos en los efectivos."""
    from app.models.asignacion import Asignacion, RolDominio
    from app.repositories.rbac_repository import RbacRepository

    # Sin asignación, no tiene permisos
    perms_antes = await RbacRepository.get_effective_permissions(db_session, test_user, tenant_id)

    # Crear asignación vigente
    asig = Asignacion(
        tenant_id=tenant_id,
        usuario_id=test_user,
        rol=RolDominio.PROFESOR,
        desde=date.today() - timedelta(days=5),
        hasta=None,
        comisiones=[],
    )
    db_session.add(asig)
    await db_session.commit()

    perms_despues = await RbacRepository.get_effective_permissions(db_session, test_user, tenant_id)
    expected_perms = await _get_perms_for_profesor(db_session, tenant_id)

    if not expected_perms:
        pytest.skip("No hay permisos definidos para PROFESOR en el catálogo")

    # Los permisos del rol PROFESOR deben estar ahora presentes
    for p in expected_perms:
        assert p in perms_despues, f"Permiso {p} debe estar en permisos efectivos tras asignación vigente"


# ── 8.2 Asignación vencida → no contribuye ────────────────────────────────────

@pytest.mark.asyncio
async def test_asignacion_vencida_no_agrega_permisos(db_session, tenant_id, test_user, profesor_rol_id):
    """Asignación vencida (hasta en pasado) no contribuye permisos."""
    from app.models.asignacion import Asignacion, RolDominio
    from app.repositories.rbac_repository import RbacRepository

    expected_perms = await _get_perms_for_profesor(db_session, tenant_id)
    if not expected_perms:
        pytest.skip("No hay permisos definidos para PROFESOR en el catálogo")

    # Crear asignación YA vencida
    asig = Asignacion(
        tenant_id=tenant_id,
        usuario_id=test_user,
        rol=RolDominio.PROFESOR,
        desde=date.today() - timedelta(days=30),
        hasta=date.today() - timedelta(days=1),  # vencida ayer
        comisiones=[],
    )
    db_session.add(asig)
    await db_session.commit()

    perms = await RbacRepository.get_effective_permissions(db_session, test_user, tenant_id)

    # Los permisos de PROFESOR NO deben aparecer (asignación vencida)
    for p in expected_perms:
        assert p not in perms, f"Permiso {p} NO debe estar: asignación vencida"


# ── 8.4 Soft delete quita permiso en siguiente request ───────────────────────

@pytest.mark.asyncio
async def test_soft_delete_quita_permiso(db_session, tenant_id, test_user, profesor_rol_id):
    """Después de soft delete de asignación vigente, permisos no incluyen los del rol."""
    from app.models.asignacion import Asignacion, RolDominio
    from app.repositories.rbac_repository import RbacRepository
    from app.repositories.asignacion_repository import AsignacionRepository

    expected_perms = await _get_perms_for_profesor(db_session, tenant_id)
    if not expected_perms:
        pytest.skip("No hay permisos definidos para PROFESOR en el catálogo")

    # Crear asignación vigente
    asig_repo = AsignacionRepository(db_session)
    asig = await asig_repo.create(tenant_id, {
        "usuario_id": test_user,
        "rol": "PROFESOR",
        "desde": date.today() - timedelta(days=5),
        "hasta": None,
        "comisiones": [],
    })

    # Verificar que tiene permisos
    perms_con_asig = await RbacRepository.get_effective_permissions(db_session, test_user, tenant_id)
    for p in expected_perms:
        assert p in perms_con_asig, f"Permiso {p} debe estar antes del soft delete"

    # Soft delete
    await asig_repo.soft_delete(asig.id, tenant_id)

    # Ahora no debe tener esos permisos
    perms_sin_asig = await RbacRepository.get_effective_permissions(db_session, test_user, tenant_id)
    for p in expected_perms:
        assert p not in perms_sin_asig, f"Permiso {p} NO debe estar después del soft delete"
