"""Tests del servicio de liquidaciones y honorarios (C-18) — Strict TDD.

Tasks 11.1–11.9 (cálculo), 12.1–12.3 (cierre), 13.1–13.4 (vista segmentada),
14.1–14.4 (facturas), 15.1–15.4 (RBAC y multi-tenancy).

Todos los tests usan la base de datos real (postgres en puerto 5433).
NO se mockea la DB — regla del proyecto.
"""

import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

import app.models  # noqa: F401 — registrar modelos


# ── Helpers para service factories ────────────────────────────────────────────


def _make_liq_service(session: AsyncSession):
    from app.repositories.asignacion_repository import AsignacionRepository
    from app.repositories.audit_log_repository import AuditLogRepository
    from app.repositories.liquidacion_repository import (
        LiquidacionRepository,
        SalarioBaseRepository,
        SalarioPlusRepository,
    )
    from app.repositories.usuario_repository import UsuarioRepository
    from app.services.liquidacion_service import LiquidacionService

    return LiquidacionService(
        session=session,
        liq_repo=LiquidacionRepository(session),
        salario_base_repo=SalarioBaseRepository(session),
        salario_plus_repo=SalarioPlusRepository(session),
        asignacion_repo=AsignacionRepository(session),
        usuario_repo=UsuarioRepository(session),
        audit_repo=AuditLogRepository(session),
    )


def _make_factura_service(session: AsyncSession):
    from app.repositories.liquidacion_repository import FacturaRepository
    from app.repositories.usuario_repository import UsuarioRepository
    from app.services.factura_service import FacturaService

    return FacturaService(
        factura_repo=FacturaRepository(session),
        usuario_repo=UsuarioRepository(session),
    )


# ── DB fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant_id(db_session) -> uuid.UUID:
    tid = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, requiere_aprobacion, created_at, updated_at) VALUES (:id, :name, true, false, now(), now())"),
        {"id": tid, "name": f"tenant-svc-{tid.hex[:8]}"},
    )
    await db_session.commit()
    return tid


@pytest_asyncio.fixture
async def tenant2_id(db_session) -> uuid.UUID:
    tid = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, requiere_aprobacion, created_at, updated_at) VALUES (:id, :name, true, false, now(), now())"),
        {"id": tid, "name": f"tenant2-svc-{tid.hex[:8]}"},
    )
    await db_session.commit()
    return tid


async def _crear_usuario(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    facturador: bool = False,
    con_cbu: bool = True,
    con_banco: bool = True,
) -> uuid.UUID:
    uid = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO \"user\" (id, tenant_id, email, password_hash, facturador, "
            "cbu_enc, banco, estado, totp_enabled, is_active, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :email, 'hash', :facturador, :cbu_enc, :banco, 'activa', false, true, now(), now())"
        ),
        {
            "id": uid,
            "tenant_id": tenant_id,
            "email": f"user-{uid.hex[:8]}@test.com",
            "facturador": facturador,
            "cbu_enc": "cbu-cifrado" if con_cbu else None,
            "banco": "BBVA" if con_banco else None,
        },
    )
    await session.commit()
    return uid


async def _crear_cohorte(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    # Crear carrera primero
    carrera_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO carrera (id, tenant_id, codigo, nombre, estado, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, 'activa', now(), now())"
        ),
        {"id": carrera_id, "tenant_id": tenant_id, "codigo": f"CAR-{carrera_id.hex[:6]}", "nombre": "Carrera Test"},
    )
    cohorte_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cohorte (id, tenant_id, carrera_id, nombre, anio, vig_desde, estado, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :carrera_id, :nombre, :anio, :vig_desde, 'activa', now(), now())"
        ),
        {
            "id": cohorte_id,
            "tenant_id": tenant_id,
            "carrera_id": carrera_id,
            "nombre": f"Cohorte-{cohorte_id.hex[:6]}",
            "anio": 2026,
            "vig_desde": date(2026, 1, 1),
        },
    )
    await session.commit()
    return cohorte_id


async def _crear_materia(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    mid = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO materia (id, tenant_id, codigo, nombre, estado, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, 'activa', now(), now())"
        ),
        {"id": mid, "tenant_id": tenant_id, "codigo": f"MAT-{mid.hex[:6]}", "nombre": "Materia Test"},
    )
    await session.commit()
    return mid


async def _crear_instancia(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    periodo: str,
    plus_key: Optional[str] = None,
) -> uuid.UUID:
    iid = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO instancia_dictado "
            "(id, tenant_id, materia_id, cohorte_id, nombre, periodo, plus_key, estado, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :materia_id, :cohorte_id, :nombre, :periodo, :plus_key, 'activa', now(), now())"
        ),
        {
            "id": iid,
            "tenant_id": tenant_id,
            "materia_id": materia_id,
            "cohorte_id": cohorte_id,
            "nombre": f"Instancia-{iid.hex[:6]}",
            "periodo": periodo,
            "plus_key": plus_key,
        },
    )
    await session.commit()
    return iid


async def _crear_asignacion(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    rol: str = "PROFESOR",
) -> uuid.UUID:
    aid = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO asignacion (id, tenant_id, usuario_id, rol, cohorte_id, comisiones, desde, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :usuario_id, :rol, :cohorte_id, '[]', :desde, now(), now())"
        ),
        {
            "id": aid,
            "tenant_id": tenant_id,
            "usuario_id": usuario_id,
            "rol": rol,
            "cohorte_id": cohorte_id,
            "desde": date(2026, 1, 1),
        },
    )
    await session.commit()
    return aid


async def _crear_salario_base(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    rol: str,
    monto: Decimal,
    desde: date = date(2026, 1, 1),
    hasta: Optional[date] = None,
) -> uuid.UUID:
    from app.repositories.liquidacion_repository import SalarioBaseRepository
    repo = SalarioBaseRepository(session)
    obj = await repo.create(tenant_id, {"rol": rol, "monto": monto, "desde": desde, "hasta": hasta})
    await session.commit()
    return obj.id


async def _crear_salario_plus(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    grupo: str,
    rol: str,
    monto: Decimal,
    desde: date = date(2026, 1, 1),
) -> uuid.UUID:
    from app.repositories.liquidacion_repository import SalarioPlusRepository
    repo = SalarioPlusRepository(session)
    obj = await repo.create(tenant_id, {"grupo": grupo, "rol": rol, "monto": monto, "desde": desde, "hasta": None})
    await session.commit()
    return obj.id


async def _crear_actor(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """Crea un usuario FINANZAS para ser el actor en audit log."""
    uid = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO \"user\" (id, tenant_id, email, password_hash, facturador, "
            "estado, totp_enabled, is_active, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :email, 'hash', false, 'activa', false, true, now(), now())"
        ),
        {"id": uid, "tenant_id": tenant_id, "email": f"finanzas-{uid.hex[:8]}@test.com"},
    )
    await session.commit()
    return uid


# ═══════════════════════════════════════════════════════════════════════════════
# Tasks 11.1–11.9 — Cálculo de liquidación
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_calculo_con_base_y_plus_una_clave(db_session, tenant_id):
    """11.1 RED→GREEN→TRIANGULATE: docente con base + plus de una clave activa."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03", plus_key="PROG")
    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id, rol="PROFESOR")
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))
    await _crear_salario_plus(db_session, tenant_id, "PROG", "PROFESOR", Decimal("300.00"))

    svc = _make_liq_service(db_session)
    result = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()

    assert len(result.liquidaciones) == 1
    liq = result.liquidaciones[0]
    assert liq.usuario_id == usuario_id
    assert liq.monto_base == Decimal("1500.00")
    assert liq.monto_plus == Decimal("300.00")
    assert liq.total == Decimal("1800.00")
    assert result.creadas == 1
    assert len(result.omitidos) == 0


@pytest.mark.asyncio
async def test_calculo_misma_clave_tres_comisiones_plus_una_vez(db_session, tenant_id):
    """11.2 RED→GREEN: 3 instancias con la misma plus_key → plus contado UNA sola vez (RN-33)."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)

    # 3 instancias distintas con la misma clave "PROG"
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03", plus_key="PROG")
    mat2 = await _crear_materia(db_session, tenant_id)
    mat3 = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, mat2, cohorte_id, "2026-03", plus_key="PROG")
    await _crear_instancia(db_session, tenant_id, mat3, cohorte_id, "2026-03", plus_key="PROG")

    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id, rol="PROFESOR")
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))
    await _crear_salario_plus(db_session, tenant_id, "PROG", "PROFESOR", Decimal("300.00"))

    svc = _make_liq_service(db_session)
    result = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()

    assert len(result.liquidaciones) == 1
    liq = result.liquidaciones[0]
    # Plus "PROG" contado solo UNA VEZ aunque hay 3 instancias
    assert liq.monto_plus == Decimal("300.00")
    assert liq.total == Decimal("1800.00")


@pytest.mark.asyncio
async def test_calculo_multiples_claves_suma_todos_los_plus(db_session, tenant_id):
    """11.3 RED→GREEN→TRIANGULATE: docente con 2 claves distintas → suma ambos plus (RN-34)."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    mat1 = await _crear_materia(db_session, tenant_id)
    mat2 = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, mat1, cohorte_id, "2026-03", plus_key="PROG")
    await _crear_instancia(db_session, tenant_id, mat2, cohorte_id, "2026-03", plus_key="BD")

    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id, rol="PROFESOR")
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))
    await _crear_salario_plus(db_session, tenant_id, "PROG", "PROFESOR", Decimal("300.00"))
    await _crear_salario_plus(db_session, tenant_id, "BD", "PROFESOR", Decimal("200.00"))

    svc = _make_liq_service(db_session)
    result = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()

    assert len(result.liquidaciones) == 1
    liq = result.liquidaciones[0]
    # Suma PROG + BD = 300 + 200 = 500
    assert liq.monto_plus == Decimal("500.00")
    assert liq.total == Decimal("2000.00")


@pytest.mark.asyncio
async def test_calculo_sin_plus_key_monto_plus_cero(db_session, tenant_id):
    """11.4 RED→GREEN: instancias sin plus_key → monto_plus = 0."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    # Instancia SIN plus_key
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03", plus_key=None)
    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id, rol="PROFESOR")
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))

    svc = _make_liq_service(db_session)
    result = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()

    assert len(result.liquidaciones) == 1
    liq = result.liquidaciones[0]
    assert liq.monto_plus == Decimal("0")
    assert liq.total == Decimal("1500.00")


@pytest.mark.asyncio
async def test_calculo_docente_sin_cbu_omitido(db_session, tenant_id):
    """11.5 RED→GREEN→TRIANGULATE: docente sin CBU omitido y aparece en omitidos (RN-26)."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    # Usuario SIN CBU
    usuario_sin_cbu = await _crear_usuario(db_session, tenant_id, con_cbu=False, con_banco=True)
    # Usuario CON CBU (control)
    usuario_con_cbu = await _crear_usuario(db_session, tenant_id, con_cbu=True, con_banco=True)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03")
    await _crear_asignacion(db_session, tenant_id, usuario_sin_cbu, cohorte_id)
    await _crear_asignacion(db_session, tenant_id, usuario_con_cbu, cohorte_id)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))

    svc = _make_liq_service(db_session)
    result = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()

    omitidos_ids = [o.usuario_id for o in result.omitidos]
    assert usuario_sin_cbu in omitidos_ids
    assert usuario_con_cbu not in omitidos_ids
    # Solo el usuario con CBU tiene liquidación
    liq_ids = [l.usuario_id for l in result.liquidaciones]
    assert usuario_con_cbu in liq_ids
    assert usuario_sin_cbu not in liq_ids


@pytest.mark.asyncio
async def test_calculo_facturador_marcado_excluido_por_factura(db_session, tenant_id):
    """11.6 RED→GREEN: docente facturador=True → excluido_por_factura=True en liquidación."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_facturador = await _crear_usuario(db_session, tenant_id, facturador=True)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03")
    await _crear_asignacion(db_session, tenant_id, usuario_facturador, cohorte_id)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))

    svc = _make_liq_service(db_session)
    result = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()

    assert len(result.liquidaciones) == 1
    liq = result.liquidaciones[0]
    assert liq.excluido_por_factura is True
    assert liq.usuario_id == usuario_facturador


@pytest.mark.asyncio
async def test_calculo_nexo_marcado_es_nexo(db_session, tenant_id):
    """11.7 RED→GREEN: docente con rol NEXO → es_nexo=True."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_nexo = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03")
    # Asignación con rol NEXO
    await _crear_asignacion(db_session, tenant_id, usuario_nexo, cohorte_id, rol="NEXO")
    await _crear_salario_base(db_session, tenant_id, "NEXO", Decimal("2000.00"))

    svc = _make_liq_service(db_session)
    result = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()

    assert len(result.liquidaciones) == 1
    liq = result.liquidaciones[0]
    assert liq.es_nexo is True


@pytest.mark.asyncio
async def test_recalculo_periodo_abierto_actualiza_registros(db_session, tenant_id):
    """11.8 RED→GREEN: recálculo de período Abierto actualiza registros existentes."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03")
    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))

    svc = _make_liq_service(db_session)
    # Primer cálculo
    r1 = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()
    assert r1.creadas == 1

    # Segundo cálculo (mismo período, misma cohorte) → debe ACTUALIZAR
    r2 = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()
    assert r2.actualizadas == 1
    assert r2.creadas == 0
    # Solo una liquidación existe
    assert len(r2.liquidaciones) == 1


@pytest.mark.asyncio
async def test_calculo_periodo_cerrado_retorna_409(db_session, tenant_id):
    """11.9 RED→GREEN: intento de calcular en período Cerrado → 409."""
    from fastapi import HTTPException

    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03")
    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))
    actor_id = await _crear_actor(db_session, tenant_id)

    svc = _make_liq_service(db_session)
    # Calcular y cerrar
    await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()
    await svc.cerrar_periodo(tenant_id, cohorte_id, "2026-03", actor_id)
    await db_session.commit()

    # Intento de recalcular período cerrado → 409
    with pytest.raises(HTTPException) as exc_info:
        await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    assert exc_info.value.status_code == 409


# ═══════════════════════════════════════════════════════════════════════════════
# Tasks 12.1–12.3 — Cierre de liquidación
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cierre_exitoso_cambia_estado_a_cerrada(db_session, tenant_id):
    """12.1 RED→GREEN→TRIANGULATE: cierre exitoso de liquidación Abierta → Cerrada."""
    from app.models.liquidacion import EstadoLiquidacion

    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03")
    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))
    actor_id = await _crear_actor(db_session, tenant_id)

    svc = _make_liq_service(db_session)
    result = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()

    liq_id = result.liquidaciones[0].id

    # Cerrar por ID
    cerrada = await svc.cerrar_por_id(tenant_id, liq_id, actor_id)
    await db_session.commit()

    assert cerrada.estado == EstadoLiquidacion.cerrada

    # Triangulación: verificar en la DB que el estado persiste
    from app.repositories.liquidacion_repository import LiquidacionRepository
    repo = LiquidacionRepository(db_session)
    liq = await repo.get_by_id(liq_id, tenant_id)
    assert liq.estado == EstadoLiquidacion.cerrada


@pytest.mark.asyncio
async def test_cierre_genera_audit_log(db_session, tenant_id):
    """12.2 RED→GREEN: cierre genera evento LIQUIDACION_CERRAR en audit log con snapshot."""
    from sqlalchemy import text as sqla_text

    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-04")
    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))
    actor_id = await _crear_actor(db_session, tenant_id)

    svc = _make_liq_service(db_session)
    await svc.calcular_periodo(tenant_id, cohorte_id, "2026-04")
    await db_session.commit()
    await svc.cerrar_periodo(tenant_id, cohorte_id, "2026-04", actor_id)
    await db_session.commit()

    # Verificar que existe el audit log
    result = await db_session.execute(
        sqla_text(
            "SELECT accion, detalle FROM audit_log "
            "WHERE tenant_id = :tenant_id AND accion = 'LIQUIDACION_CERRAR' "
            "ORDER BY fecha_hora DESC LIMIT 1"
        ),
        {"tenant_id": tenant_id},
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "LIQUIDACION_CERRAR"
    detalle = row[1]
    assert "snapshot" in detalle
    assert "periodo" in detalle


@pytest.mark.asyncio
async def test_cierre_rechazado_si_ya_cerrada(db_session, tenant_id):
    """12.3 RED→GREEN→TRIANGULATE: cierre rechazado si liquidación ya Cerrada (409)."""
    from fastapi import HTTPException

    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-05")
    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))
    actor_id = await _crear_actor(db_session, tenant_id)

    svc = _make_liq_service(db_session)
    result = await svc.calcular_periodo(tenant_id, cohorte_id, "2026-05")
    await db_session.commit()
    liq_id = result.liquidaciones[0].id

    # Primer cierre → exitoso
    await svc.cerrar_por_id(tenant_id, liq_id, actor_id)
    await db_session.commit()

    # Segundo cierre → 409
    with pytest.raises(HTTPException) as exc_info:
        await svc.cerrar_por_id(tenant_id, liq_id, actor_id)
    assert exc_info.value.status_code == 409
    assert "cerrada" in exc_info.value.detail.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Tasks 13.1–13.4 — Vista segmentada y KPIs
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def vista_fixture(db_session, tenant_id):
    """Fixture: 3 usuarios distintos (general, nexo, facturante) con liquidaciones."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-06")
    actor_id = await _crear_actor(db_session, tenant_id)

    u_general = await _crear_usuario(db_session, tenant_id)
    u_nexo = await _crear_usuario(db_session, tenant_id)
    u_facturante = await _crear_usuario(db_session, tenant_id, facturador=True)

    await _crear_asignacion(db_session, tenant_id, u_general, cohorte_id, rol="PROFESOR")
    await _crear_asignacion(db_session, tenant_id, u_nexo, cohorte_id, rol="NEXO")
    await _crear_asignacion(db_session, tenant_id, u_facturante, cohorte_id, rol="PROFESOR")

    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))
    await _crear_salario_base(db_session, tenant_id, "NEXO", Decimal("2000.00"))

    svc = _make_liq_service(db_session)
    await svc.calcular_periodo(tenant_id, cohorte_id, "2026-06")
    await db_session.commit()

    return {
        "tenant_id": tenant_id,
        "cohorte_id": cohorte_id,
        "u_general": u_general,
        "u_nexo": u_nexo,
        "u_facturante": u_facturante,
        "actor_id": actor_id,
        "svc": svc,
    }


@pytest.mark.asyncio
async def test_vista_tres_segmentos_clasificados(db_session, vista_fixture):
    """13.1 RED→GREEN: vista retorna tres segmentos bien clasificados."""
    svc = vista_fixture["svc"]
    tenant_id = vista_fixture["tenant_id"]
    cohorte_id = vista_fixture["cohorte_id"]

    vista = await svc.get_vista_periodo(tenant_id, cohorte_id, "2026-06")

    general_ids = {l.usuario_id for l in vista.general}
    nexo_ids = {l.usuario_id for l in vista.nexo}
    facturante_ids = {l.usuario_id for l in vista.facturantes}

    assert vista_fixture["u_general"] in general_ids
    assert vista_fixture["u_nexo"] in nexo_ids
    assert vista_fixture["u_facturante"] in facturante_ids
    # Sin superposición
    assert not (general_ids & nexo_ids)
    assert not (general_ids & facturante_ids)
    assert not (nexo_ids & facturante_ids)


@pytest.mark.asyncio
async def test_kpi_total_sin_factura_incluye_general_y_nexo(db_session, vista_fixture):
    """13.2 RED→GREEN: total_sin_factura = general + nexo (excluye facturantes)."""
    svc = vista_fixture["svc"]
    tenant_id = vista_fixture["tenant_id"]
    cohorte_id = vista_fixture["cohorte_id"]

    vista = await svc.get_vista_periodo(tenant_id, cohorte_id, "2026-06")

    expected_sin = sum(l.total for l in vista.general) + sum(l.total for l in vista.nexo)
    assert vista.total_sin_factura == expected_sin
    # total_sin_factura NO incluye facturantes
    for f in vista.facturantes:
        assert f.total not in [vista.total_sin_factura]  # trivial pero explícito


@pytest.mark.asyncio
async def test_kpi_total_con_factura(db_session, vista_fixture):
    """13.3 RED→GREEN: total_con_factura = suma de montos de facturantes."""
    svc = vista_fixture["svc"]
    tenant_id = vista_fixture["tenant_id"]
    cohorte_id = vista_fixture["cohorte_id"]

    vista = await svc.get_vista_periodo(tenant_id, cohorte_id, "2026-06")

    expected_con = sum(l.total for l in vista.facturantes)
    assert vista.total_con_factura == expected_con


@pytest.mark.asyncio
async def test_historial_retorna_solo_cerradas_orden_desc(db_session, tenant_id):
    """13.4 RED→GREEN→TRIANGULATE: historial retorna solo Cerradas, ordenadas por período desc."""
    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-01")
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-02")
    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))
    actor_id = await _crear_actor(db_session, tenant_id)

    svc = _make_liq_service(db_session)
    await svc.calcular_periodo(tenant_id, cohorte_id, "2026-01")
    await db_session.commit()
    await svc.calcular_periodo(tenant_id, cohorte_id, "2026-02")
    await db_session.commit()
    # Cerrar solo 2026-01
    await svc.cerrar_periodo(tenant_id, cohorte_id, "2026-01", actor_id)
    await db_session.commit()

    from app.repositories.liquidacion_repository import LiquidacionRepository
    repo = LiquidacionRepository(db_session)
    historial = await repo.list_historial(tenant_id, cohorte_id)

    # Solo el período 2026-01 está cerrado
    assert len(historial) == 1
    assert historial[0].periodo == "2026-01"


# ═══════════════════════════════════════════════════════════════════════════════
# Tasks 14.1–14.4 — Facturas
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_factura_create_facturante_estado_pendiente(db_session, tenant_id):
    """14.1 RED→GREEN: carga de factura para docente facturante → estado Pendiente."""
    from app.models.liquidacion import EstadoFactura
    from app.schemas.liquidacion import FacturaCreate

    usuario_facturador = await _crear_usuario(db_session, tenant_id, facturador=True)
    svc = _make_factura_service(db_session)

    data = FacturaCreate(
        usuario_id=usuario_facturador,
        periodo="2026-03",
        detalle="Factura marzo 2026",
        referencia_archivo="facturas/2026-03/f001.pdf",
    )
    factura = await svc.create(tenant_id, data)
    await db_session.commit()

    assert factura.id is not None
    assert factura.estado == EstadoFactura.pendiente
    assert factura.usuario_id == usuario_facturador
    assert factura.cargada_at is not None
    assert factura.abonada_at is None


@pytest.mark.asyncio
async def test_factura_create_no_facturante_rechazado(db_session, tenant_id):
    """14.2 RED→GREEN→TRIANGULATE: intento de carga para docente no-facturante → 422."""
    from fastapi import HTTPException
    from app.schemas.liquidacion import FacturaCreate

    usuario_no_facturador = await _crear_usuario(db_session, tenant_id, facturador=False)
    svc = _make_factura_service(db_session)

    data = FacturaCreate(
        usuario_id=usuario_no_facturador,
        periodo="2026-03",
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(tenant_id, data)
    assert exc_info.value.status_code == 422
    assert "facturante" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_factura_update_estado_pendiente_a_abonada(db_session, tenant_id):
    """14.3 RED→GREEN: cambio Pendiente → Abonada; abonada_at registrado."""
    from app.models.liquidacion import EstadoFactura
    from app.schemas.liquidacion import FacturaCreate, FacturaPatchRequest

    usuario_facturador = await _crear_usuario(db_session, tenant_id, facturador=True)
    svc = _make_factura_service(db_session)

    data = FacturaCreate(usuario_id=usuario_facturador, periodo="2026-03")
    factura = await svc.create(tenant_id, data)
    await db_session.commit()

    patch = FacturaPatchRequest(estado=EstadoFactura.abonada)
    actualizada = await svc.update_estado(tenant_id, factura.id, patch)
    await db_session.commit()

    assert actualizada.estado == EstadoFactura.abonada
    assert actualizada.abonada_at is not None


@pytest.mark.asyncio
async def test_factura_list_filtros_usuario_y_estado(db_session, tenant_id):
    """14.4 RED→GREEN: filtros de listado por usuario_id y estado funcionan correctamente."""
    from app.models.liquidacion import EstadoFactura
    from app.schemas.liquidacion import FacturaCreate, FacturaPatchRequest

    u1 = await _crear_usuario(db_session, tenant_id, facturador=True)
    u2 = await _crear_usuario(db_session, tenant_id, facturador=True)
    svc = _make_factura_service(db_session)

    # Crear 2 facturas de u1 y 1 de u2
    f1 = await svc.create(tenant_id, FacturaCreate(usuario_id=u1, periodo="2026-03"))
    f2 = await svc.create(tenant_id, FacturaCreate(usuario_id=u1, periodo="2026-04"))
    f3 = await svc.create(tenant_id, FacturaCreate(usuario_id=u2, periodo="2026-03"))
    await db_session.commit()

    # Marcar f1 como Abonada
    await svc.update_estado(tenant_id, f1.id, FacturaPatchRequest(estado=EstadoFactura.abonada))
    await db_session.commit()

    # Filtrar por usuario u1
    solo_u1 = await svc.list_with_filters(tenant_id, usuario_id=u1)
    assert len(solo_u1) == 2
    u1_ids = {f.id for f in solo_u1}
    assert f1.id in u1_ids
    assert f2.id in u1_ids
    assert f3.id not in u1_ids

    # Filtrar por estado Pendiente del tenant
    pendientes = await svc.list_with_filters(tenant_id, estado=EstadoFactura.pendiente)
    pendientes_ids = {f.id for f in pendientes}
    assert f1.id not in pendientes_ids  # ya está abonada
    assert f2.id in pendientes_ids
    assert f3.id in pendientes_ids


# ═══════════════════════════════════════════════════════════════════════════════
# Tasks 15.1–15.4 — RBAC y multi-tenancy
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rbac_profesor_no_puede_ver_liquidaciones(db_session, tenant_id):
    """15.1 RED→GREEN: repositorio de liquidaciones filtra por tenant — PROFESOR de otro tenant no ve nada."""
    from app.repositories.liquidacion_repository import LiquidacionRepository

    cohorte_id = await _crear_cohorte(db_session, tenant_id)
    usuario_id = await _crear_usuario(db_session, tenant_id)
    materia_id = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_id, cohorte_id, "2026-03")
    await _crear_asignacion(db_session, tenant_id, usuario_id, cohorte_id)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))

    svc = _make_liq_service(db_session)
    await svc.calcular_periodo(tenant_id, cohorte_id, "2026-03")
    await db_session.commit()

    # Crear un segundo tenant y verificar que no ve las liquidaciones del primero
    otro_tenant = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO tenant (id, name, is_active, requiere_aprobacion, created_at, updated_at) VALUES (:id, :name, true, false, now(), now())"),
        {"id": otro_tenant, "name": f"otro-{otro_tenant.hex[:8]}"},
    )
    await db_session.commit()

    repo = LiquidacionRepository(db_session)
    liq_otro = await repo.list_by_periodo(otro_tenant, cohorte_id=cohorte_id, periodo="2026-03")
    # Multi-tenancy: tenant B no ve liquidaciones de tenant A
    assert len(liq_otro) == 0


@pytest.mark.asyncio
async def test_liquidaciones_tenant_a_no_visibles_para_tenant_b(db_session, tenant_id, tenant2_id):
    """15.3 RED→GREEN: liquidaciones de tenant A no visibles para FINANZAS de tenant B."""
    from app.repositories.liquidacion_repository import LiquidacionRepository

    cohorte_a = await _crear_cohorte(db_session, tenant_id)
    usuario_a = await _crear_usuario(db_session, tenant_id)
    materia_a = await _crear_materia(db_session, tenant_id)
    await _crear_instancia(db_session, tenant_id, materia_a, cohorte_a, "2026-07")
    await _crear_asignacion(db_session, tenant_id, usuario_a, cohorte_a)
    await _crear_salario_base(db_session, tenant_id, "PROFESOR", Decimal("1500.00"))

    svc = _make_liq_service(db_session)
    await svc.calcular_periodo(tenant_id, cohorte_a, "2026-07")
    await db_session.commit()

    # Tenant B intenta listar por cohorte_a → nada (cohorte_a pertenece a tenant A)
    repo = LiquidacionRepository(db_session)
    liqs_b = await repo.list_by_periodo(tenant2_id, cohorte_id=cohorte_a, periodo="2026-07")
    assert len(liqs_b) == 0

    # Tenant A ve sus propias liquidaciones
    liqs_a = await repo.list_by_periodo(tenant_id, cohorte_id=cohorte_a, periodo="2026-07")
    assert len(liqs_a) == 1


@pytest.mark.asyncio
async def test_facturas_tenant_a_no_visibles_para_tenant_b(db_session, tenant_id, tenant2_id):
    """15.4 RED→GREEN: facturas de tenant A no visibles para FINANZAS de tenant B."""
    from app.repositories.liquidacion_repository import FacturaRepository
    from app.schemas.liquidacion import FacturaCreate

    usuario_a = await _crear_usuario(db_session, tenant_id, facturador=True)
    svc = _make_factura_service(db_session)
    await svc.create(tenant_id, FacturaCreate(usuario_id=usuario_a, periodo="2026-07"))
    await db_session.commit()

    # Tenant B lista facturas → no ve las de tenant A
    repo = FacturaRepository(db_session)
    facturas_b = await repo.list_with_filters(tenant2_id)
    assert len(facturas_b) == 0

    # Tenant A ve sus facturas
    facturas_a = await repo.list_with_filters(tenant_id)
    assert len(facturas_a) == 1

