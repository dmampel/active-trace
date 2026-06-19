"""Tests de repositorios de liquidaciones (C-18) — Strict TDD.

Tasks 10.1–10.6 (grilla salarial):
  10.1 - Alta de SalarioBase exitosa
  10.2 - Alta de SalarioBase rechazada por solapamiento de vigencia
  10.3 - get_vigente_para_periodo retorna el registro correcto según fecha
  10.4 - get_vigente_para_periodo retorna None si no hay registro vigente
  10.5 - Alta de SalarioPlus exitosa
  10.6 - Lista de grilla salarial del tenant
"""

import os
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

import app.models  # noqa: F401 — registrar todos los modelos (incluyendo liquidacion)


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant_id(db_session) -> uuid.UUID:
    tid = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, requiere_aprobacion, created_at, updated_at) VALUES (:id, :name, true, false, now(), now())"),
        {"id": tid, "name": f"tenant-liq-{tid.hex[:8]}"},
    )
    await db_session.commit()
    return tid


@pytest_asyncio.fixture
async def tenant2_id(db_session) -> uuid.UUID:
    tid = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, requiere_aprobacion, created_at, updated_at) VALUES (:id, :name, true, false, now(), now())"),
        {"id": tid, "name": f"tenant2-liq-{tid.hex[:8]}"},
    )
    await db_session.commit()
    return tid


# ── Helpers ───────────────────────────────────────────────────────────────────


def _base_repo(session):
    from app.repositories.liquidacion_repository import SalarioBaseRepository
    return SalarioBaseRepository(session)


def _plus_repo(session):
    from app.repositories.liquidacion_repository import SalarioPlusRepository
    return SalarioPlusRepository(session)


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10.1 — Alta de SalarioBase exitosa
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_salario_base_create_exitoso(db_session, tenant_id):
    """10.1 RED→GREEN→TRIANGULATE: SalarioBase se crea correctamente con todos los campos."""
    repo = _base_repo(db_session)

    # Caso 1: salario base sin hasta (vigencia abierta)
    obj = await repo.create(tenant_id, {
        "rol": "PROFESOR",
        "monto": Decimal("1500.00"),
        "desde": date(2026, 1, 1),
        "hasta": None,
    })
    await db_session.commit()

    assert obj.id is not None
    assert obj.tenant_id == tenant_id
    assert obj.rol == "PROFESOR"
    assert obj.monto == Decimal("1500.00")
    assert obj.desde == date(2026, 1, 1)
    assert obj.hasta is None
    assert obj.deleted_at is None

    # Triangulación: salario base con hasta definido (un rol distinto)
    obj2 = await repo.create(tenant_id, {
        "rol": "TUTOR",
        "monto": Decimal("1200.50"),
        "desde": date(2026, 3, 1),
        "hasta": date(2026, 12, 31),
    })
    await db_session.commit()

    assert obj2.rol == "TUTOR"
    assert obj2.monto == Decimal("1200.50")
    assert obj2.hasta == date(2026, 12, 31)


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10.2 — Alta de SalarioBase rechazada por solapamiento
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_salario_base_check_solapamiento_detecta_conflicto(db_session, tenant_id):
    """10.2 RED→GREEN→TRIANGULATE: check_solapamiento detecta rangos que se cruzan."""
    repo = _base_repo(db_session)

    # Crear un salario base existente para PROFESOR: 2026-01-01 hasta NULL
    await repo.create(tenant_id, {
        "rol": "PROFESOR",
        "monto": Decimal("1500.00"),
        "desde": date(2026, 1, 1),
        "hasta": None,
    })
    await db_session.commit()

    # Caso 1: nuevo rango 2026-06-01 hasta NULL → solapa con el existente abierto
    solapa1 = await repo.check_solapamiento(tenant_id, "PROFESOR", date(2026, 6, 1), None)
    assert solapa1 is True

    # Triangulación: nuevo rango 2025-01-01 hasta 2026-03-31 → también solapa
    solapa2 = await repo.check_solapamiento(tenant_id, "PROFESOR", date(2025, 1, 1), date(2026, 3, 31))
    assert solapa2 is True

    # Control: mismo período para TUTOR (rol distinto) → NO solapa
    no_solapa = await repo.check_solapamiento(tenant_id, "TUTOR", date(2026, 1, 1), None)
    assert no_solapa is False

    # Control: tenant2 → NO solapa (aislamiento)
    from app.repositories.liquidacion_repository import SalarioBaseRepository
    repo2 = SalarioBaseRepository(db_session)
    otro_tenant_id = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, requiere_aprobacion, created_at, updated_at) VALUES (:id, :name, true, false, now(), now())"),
        {"id": otro_tenant_id, "name": f"tenant-otro-{otro_tenant_id.hex[:8]}"},
    )
    await db_session.commit()
    no_solapa_otro = await repo2.check_solapamiento(otro_tenant_id, "PROFESOR", date(2026, 1, 1), None)
    assert no_solapa_otro is False


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10.3 — get_vigente_para_periodo retorna el correcto
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_vigente_para_periodo_retorna_correcto(db_session, tenant_id):
    """10.3 RED→GREEN→TRIANGULATE: get_vigente_para_periodo respeta la vigencia."""
    repo = _base_repo(db_session)

    # Salario base para PROFESOR: 2026-01-01 hasta 2026-06-30
    await repo.create(tenant_id, {
        "rol": "PROFESOR",
        "monto": Decimal("1500.00"),
        "desde": date(2026, 1, 1),
        "hasta": date(2026, 6, 30),
    })
    # Salario base para PROFESOR: 2026-07-01 hasta NULL (más reciente)
    await repo.create(tenant_id, {
        "rol": "PROFESOR",
        "monto": Decimal("1800.00"),
        "desde": date(2026, 7, 1),
        "hasta": None,
    })
    await db_session.commit()

    # Caso 1: período 2026-03 → debe retornar el salario de $1500
    vigente_marzo = await repo.get_vigente_para_periodo(tenant_id, "PROFESOR", "2026-03")
    assert vigente_marzo is not None
    assert vigente_marzo.monto == Decimal("1500.00")

    # Triangulación: período 2026-08 → debe retornar el salario de $1800
    vigente_agosto = await repo.get_vigente_para_periodo(tenant_id, "PROFESOR", "2026-08")
    assert vigente_agosto is not None
    assert vigente_agosto.monto == Decimal("1800.00")


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10.4 — get_vigente_para_periodo retorna None si no hay vigente
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_vigente_para_periodo_retorna_none_sin_registro(db_session, tenant_id):
    """10.4 RED→GREEN→TRIANGULATE: retorna None si no hay salario vigente."""
    repo = _base_repo(db_session)

    # Salario base para TUTOR solo en 2025
    await repo.create(tenant_id, {
        "rol": "TUTOR",
        "monto": Decimal("900.00"),
        "desde": date(2025, 1, 1),
        "hasta": date(2025, 12, 31),
    })
    await db_session.commit()

    # Caso 1: período 2026-03 → no hay registro vigente para TUTOR
    vigente = await repo.get_vigente_para_periodo(tenant_id, "TUTOR", "2026-03")
    assert vigente is None

    # Triangulación: rol COORDINADOR sin ningún salario → también None
    vigente2 = await repo.get_vigente_para_periodo(tenant_id, "COORDINADOR", "2026-03")
    assert vigente2 is None


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10.5 — Alta de SalarioPlus exitosa
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_salario_plus_create_exitoso(db_session, tenant_id):
    """10.5 RED→GREEN→TRIANGULATE: SalarioPlus se crea correctamente."""
    repo = _plus_repo(db_session)

    # Caso 1: plus para clave "PROG" × PROFESOR
    obj = await repo.create(tenant_id, {
        "grupo": "PROG",
        "rol": "PROFESOR",
        "descripcion": "Plus Programación",
        "monto": Decimal("300.00"),
        "desde": date(2026, 1, 1),
        "hasta": None,
    })
    await db_session.commit()

    assert obj.id is not None
    assert obj.tenant_id == tenant_id
    assert obj.grupo == "PROG"
    assert obj.rol == "PROFESOR"
    assert obj.monto == Decimal("300.00")
    assert obj.deleted_at is None

    # Triangulación: otra clave distinta ("BD") para el mismo rol
    obj2 = await repo.create(tenant_id, {
        "grupo": "BD",
        "rol": "PROFESOR",
        "descripcion": "Plus Base de Datos",
        "monto": Decimal("200.00"),
        "desde": date(2026, 1, 1),
        "hasta": None,
    })
    await db_session.commit()

    assert obj2.grupo == "BD"
    assert obj2.monto == Decimal("200.00")
    # Ambos coexisten para el mismo rol (no hay restricción de solapamiento en plus)
    todos = await repo.list_by_tenant(tenant_id)
    grupos = {p.grupo for p in todos}
    assert "PROG" in grupos
    assert "BD" in grupos


# ═══════════════════════════════════════════════════════════════════════════════
# Task 10.6 — Lista de grilla salarial del tenant
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_grilla_salarial_list_por_tenant(db_session, tenant_id, tenant2_id):
    """10.6 RED→GREEN→TRIANGULATE: list_by_tenant retorna solo los del tenant correcto."""
    base_repo = _base_repo(db_session)
    plus_repo = _plus_repo(db_session)

    # Crear en tenant_id
    await base_repo.create(tenant_id, {
        "rol": "PROFESOR",
        "monto": Decimal("1500.00"),
        "desde": date(2026, 1, 1),
        "hasta": None,
    })
    await plus_repo.create(tenant_id, {
        "grupo": "PROG",
        "rol": "PROFESOR",
        "monto": Decimal("300.00"),
        "desde": date(2026, 1, 1),
        "hasta": None,
    })
    # Crear en tenant2_id (no debe aparecer)
    await base_repo.create(tenant2_id, {
        "rol": "PROFESOR",
        "monto": Decimal("9999.00"),
        "desde": date(2026, 1, 1),
        "hasta": None,
    })
    await db_session.commit()

    # Caso 1: tenant_id ve solo los suyos
    bases = await base_repo.list_by_tenant(tenant_id)
    plus_list = await plus_repo.list_by_tenant(tenant_id)

    assert len(bases) == 1
    assert bases[0].monto == Decimal("1500.00")
    assert len(plus_list) == 1
    assert plus_list[0].grupo == "PROG"

    # Triangulación: tenant2_id ve solo los suyos
    bases2 = await base_repo.list_by_tenant(tenant2_id)
    assert len(bases2) == 1
    assert bases2[0].monto == Decimal("9999.00")

    plus2 = await plus_repo.list_by_tenant(tenant2_id)
    assert len(plus2) == 0
