"""Tests de integración para AuditoriaRepository (C-19, Tareas 3.1–3.6).

Usa SQLite in-memory para aislamiento sin PG real.
Valida: list_log (con/sin filtros, tenant isolation), acciones_por_dia,
        estado_comunicaciones_por_docente, interacciones_por_docente_materia,
        ultimas_acciones, y que NO expone operaciones de escritura sobre AuditLog.

TDD — RED+GREEN+TRIANGULATE por cada método del repositorio.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
import app.models  # noqa: F401 — registra todos los modelos


# ── Fixtures de DB ────────────────────────────────────────────────────────────


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


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_tenant(db: AsyncSession, name: str = "Tenant A") -> uuid.UUID:
    from app.models.tenant import Tenant
    t = Tenant(id=uuid.uuid4(), name=name)
    db.add(t)
    await db.commit()
    return t.id


async def _make_user(db: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.user import User
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nombre="Test",
        apellidos="User",
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="hash",
    )
    db.add(u)
    await db.commit()
    return u.id


async def _make_audit_log(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    accion: str = "CALIFICACIONES_IMPORTAR",
    materia_id: uuid.UUID | None = None,
    fecha_hora: datetime | None = None,
) -> uuid.UUID:
    from app.models.audit_log import AuditLog
    entry = AuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        actor_id=actor_id,
        accion=accion,
        materia_id=materia_id,
        fecha_hora=fecha_hora or datetime.now(timezone.utc),
        ip="127.0.0.1",
        user_agent="test",
    )
    db.add(entry)
    await db.commit()
    return entry.id


async def _make_comunicacion(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    enviado_por: uuid.UUID,
    materia_id: uuid.UUID,
    estado: str = "Enviado",
) -> uuid.UUID:
    from app.models.comunicacion import Comunicacion, EstadoComunicacion
    c = Comunicacion(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        enviado_por=enviado_por,
        materia_id=materia_id,
        destinatario="enc_email",
        asunto="Asunto",
        cuerpo="Cuerpo",
        estado=EstadoComunicacion(estado),
    )
    db.add(c)
    await db.commit()
    return c.id


# ── 3.1 list_log ──────────────────────────────────────────────────────────────


class TestListLog:
    """RED+GREEN+TRIANGULATE para AuditoriaRepository.list_log."""

    async def test_sin_filtros_devuelve_registros_del_tenant(self, db):
        """Caso 1: sin filtros → todos los registros del tenant, orden desc."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db, "Tenant A")
        actor_id = await _make_user(db, tenant_id)
        now = datetime.now(timezone.utc)
        await _make_audit_log(db, tenant_id, actor_id, fecha_hora=now - timedelta(hours=2))
        await _make_audit_log(db, tenant_id, actor_id, fecha_hora=now - timedelta(hours=1))

        repo = AuditoriaRepository(db)
        result = await repo.list_log(tenant_id=tenant_id)

        assert result.total >= 2
        assert len(result.items) >= 2
        # Orden descendente: el más reciente primero
        fechas = [item.fecha_hora for item in result.items]
        assert fechas == sorted(fechas, reverse=True)

    async def test_aislamiento_de_tenant(self, db):
        """Caso 2: un tenant no ve registros de otro tenant."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_a = await _make_tenant(db, "Tenant A")
        tenant_b = await _make_tenant(db, "Tenant B")
        actor_a = await _make_user(db, tenant_a)
        actor_b = await _make_user(db, tenant_b)

        await _make_audit_log(db, tenant_a, actor_a)
        await _make_audit_log(db, tenant_b, actor_b)

        repo = AuditoriaRepository(db)
        result_a = await repo.list_log(tenant_id=tenant_a)
        result_b = await repo.list_log(tenant_id=tenant_b)

        actor_ids_a = {item.actor_id for item in result_a.items}
        actor_ids_b = {item.actor_id for item in result_b.items}

        assert actor_a in actor_ids_a
        assert actor_b not in actor_ids_a
        assert actor_b in actor_ids_b
        assert actor_a not in actor_ids_b

    async def test_filtro_por_accion(self, db):
        """Caso 3 (triangulación): filtro por código de acción."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        await _make_audit_log(db, tenant_id, actor_id, accion="CALIFICACIONES_IMPORTAR")
        await _make_audit_log(db, tenant_id, actor_id, accion="COMUNICACION_ENVIAR")

        repo = AuditoriaRepository(db)
        result = await repo.list_log(tenant_id=tenant_id, accion="CALIFICACIONES_IMPORTAR")

        assert all(item.accion == "CALIFICACIONES_IMPORTAR" for item in result.items)

    async def test_filtro_por_materia_id(self, db):
        """Caso 4 (triangulación): filtro por materia_id."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_a = uuid.uuid4()
        materia_b = uuid.uuid4()
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_a)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_b)

        repo = AuditoriaRepository(db)
        result = await repo.list_log(tenant_id=tenant_id, materia_id=materia_a)

        assert all(item.materia_id == materia_a for item in result.items)

    async def test_paginacion(self, db):
        """Caso 5 (triangulación): paginación con page/page_size."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        for _ in range(5):
            await _make_audit_log(db, tenant_id, actor_id)

        repo = AuditoriaRepository(db)
        result = await repo.list_log(tenant_id=tenant_id, page=1, page_size=2)

        assert result.page == 1
        assert result.page_size == 2
        assert len(result.items) == 2
        assert result.total >= 5


# ── 3.2 acciones_por_dia ─────────────────────────────────────────────────────


class TestAccionesPorDia:
    """RED+GREEN+TRIANGULATE para AuditoriaRepository.acciones_por_dia."""

    async def test_distribucion_multi_dia(self, db):
        """Caso 1: 3 acciones el día 1, 2 el día 2."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)

        dia1 = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        dia2 = datetime(2026, 6, 2, 10, 0, 0, tzinfo=timezone.utc)

        for _ in range(3):
            await _make_audit_log(db, tenant_id, actor_id, fecha_hora=dia1)
        for _ in range(2):
            await _make_audit_log(db, tenant_id, actor_id, fecha_hora=dia2)

        repo = AuditoriaRepository(db)
        result = await repo.acciones_por_dia(tenant_id=tenant_id)

        by_date = {item.fecha: item.cantidad for item in result}
        assert by_date.get(date(2026, 6, 1), 0) == 3
        assert by_date.get(date(2026, 6, 2), 0) == 2

    async def test_dia_sin_actividad_no_aparece(self, db):
        """Caso 2 (triangulación): un día sin actividad no genera fila."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        dia = datetime(2026, 6, 5, 10, 0, 0, tzinfo=timezone.utc)
        await _make_audit_log(db, tenant_id, actor_id, fecha_hora=dia)

        repo = AuditoriaRepository(db)
        result = await repo.acciones_por_dia(tenant_id=tenant_id)

        dates = {item.fecha for item in result}
        assert date(2026, 6, 4) not in dates
        assert date(2026, 6, 5) in dates

    async def test_scope_por_materia(self, db):
        """Caso 3 (triangulación): filtrar por lista de materia_ids."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_a = uuid.uuid4()
        materia_b = uuid.uuid4()
        dia = datetime(2026, 6, 10, 10, 0, 0, tzinfo=timezone.utc)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_a, fecha_hora=dia)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_b, fecha_hora=dia)

        repo = AuditoriaRepository(db)
        result = await repo.acciones_por_dia(tenant_id=tenant_id, materia_ids=[materia_a])

        # Solo debe contar el log de materia_a
        total = sum(item.cantidad for item in result)
        assert total == 1


# ── 3.3 estado_comunicaciones_por_docente ─────────────────────────────────────


class TestEstadoComunicacionesPorDocente:
    """RED+GREEN+TRIANGULATE para AuditoriaRepository.estado_comunicaciones_por_docente."""

    async def test_distribucion_estados_docente(self, db):
        """Caso 1: docente con 2 Enviado y 1 Error."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        docente_id = await _make_user(db, tenant_id)
        materia_id = uuid.uuid4()

        await _make_comunicacion(db, tenant_id, docente_id, materia_id, estado="Enviado")
        await _make_comunicacion(db, tenant_id, docente_id, materia_id, estado="Enviado")
        await _make_comunicacion(db, tenant_id, docente_id, materia_id, estado="Error")

        repo = AuditoriaRepository(db)
        result = await repo.estado_comunicaciones_por_docente(tenant_id=tenant_id)

        by_estado = {item.estado: item.cantidad for item in result if item.enviado_por == docente_id}
        assert by_estado.get("Enviado", 0) == 2
        assert by_estado.get("Error", 0) == 1

    async def test_scope_por_materia(self, db):
        """Caso 2 (triangulación): scope por lista de materia_ids."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        docente_id = await _make_user(db, tenant_id)
        materia_a = uuid.uuid4()
        materia_b = uuid.uuid4()

        await _make_comunicacion(db, tenant_id, docente_id, materia_a, estado="Enviado")
        await _make_comunicacion(db, tenant_id, docente_id, materia_b, estado="Error")

        repo = AuditoriaRepository(db)
        result = await repo.estado_comunicaciones_por_docente(
            tenant_id=tenant_id, materia_ids=[materia_a]
        )

        # Solo debe aparecer la comunicación de materia_a
        materias_en_result = {item.materia_id for item in result}
        assert materia_a in materias_en_result
        assert materia_b not in materias_en_result

    async def test_aislamiento_tenant(self, db):
        """Caso 3 (triangulación): comunicaciones de otro tenant no visibles."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_a = await _make_tenant(db, "TA")
        tenant_b = await _make_tenant(db, "TB")
        docente_a = await _make_user(db, tenant_a)
        docente_b = await _make_user(db, tenant_b)
        materia_id = uuid.uuid4()

        await _make_comunicacion(db, tenant_a, docente_a, materia_id, estado="Enviado")
        await _make_comunicacion(db, tenant_b, docente_b, materia_id, estado="Enviado")

        repo = AuditoriaRepository(db)
        result = await repo.estado_comunicaciones_por_docente(tenant_id=tenant_a)

        docentes = {item.enviado_por for item in result}
        assert docente_a in docentes
        assert docente_b not in docentes


# ── 3.4 interacciones_por_docente_materia ────────────────────────────────────


class TestInteraccionesDocenteMateria:
    """RED+GREEN+TRIANGULATE para AuditoriaRepository.interacciones_por_docente_materia."""

    async def test_conteo_por_docente_materia_accion(self, db):
        """Caso 1: 5 acciones del mismo docente en la misma materia."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_id = uuid.uuid4()

        for _ in range(5):
            await _make_audit_log(
                db, tenant_id, actor_id,
                accion="CALIFICACIONES_IMPORTAR",
                materia_id=materia_id,
            )

        repo = AuditoriaRepository(db)
        result = await repo.interacciones_por_docente_materia(tenant_id=tenant_id)

        match = [
            item for item in result
            if item.actor_id == actor_id
            and item.materia_id == materia_id
            and item.accion == "CALIFICACIONES_IMPORTAR"
        ]
        assert len(match) == 1
        assert match[0].cantidad == 5

    async def test_scope_por_materia(self, db):
        """Caso 2 (triangulación): scope por lista de materia_ids."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_a = uuid.uuid4()
        materia_b = uuid.uuid4()

        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_a)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_b)

        repo = AuditoriaRepository(db)
        result = await repo.interacciones_por_docente_materia(
            tenant_id=tenant_id, materia_ids=[materia_a]
        )

        materias = {item.materia_id for item in result}
        assert materia_a in materias
        assert materia_b not in materias


# ── 3.5 ultimas_acciones ─────────────────────────────────────────────────────


class TestUltimasAcciones:
    """RED+GREEN+TRIANGULATE para AuditoriaRepository.ultimas_acciones."""

    async def test_limite_default(self, db):
        """Caso 1: sin límite explícito → respeta el límite pasado (semántica del repo)."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        for i in range(10):
            await _make_audit_log(db, tenant_id, actor_id)

        repo = AuditoriaRepository(db)
        result = await repo.ultimas_acciones(tenant_id=tenant_id, limite=5)

        assert len(result) <= 5

    async def test_orden_descendente(self, db):
        """Caso 2 (triangulación): resultado ordenado por fecha_hora desc."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        now = datetime.now(timezone.utc)
        await _make_audit_log(db, tenant_id, actor_id, fecha_hora=now - timedelta(hours=3))
        await _make_audit_log(db, tenant_id, actor_id, fecha_hora=now - timedelta(hours=1))
        await _make_audit_log(db, tenant_id, actor_id, fecha_hora=now - timedelta(hours=2))

        repo = AuditoriaRepository(db)
        result = await repo.ultimas_acciones(tenant_id=tenant_id, limite=10)

        fechas = [item.fecha_hora for item in result]
        assert fechas == sorted(fechas, reverse=True)

    async def test_scope_por_materia(self, db):
        """Caso 3 (triangulación): filtra por lista de materia_ids."""
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_a = uuid.uuid4()
        materia_b = uuid.uuid4()

        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_a)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_b)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=None)  # sin materia

        repo = AuditoriaRepository(db)
        result = await repo.ultimas_acciones(
            tenant_id=tenant_id, limite=10, materia_ids=[materia_a]
        )

        materias = {item.materia_id for item in result}
        assert materia_a in materias
        assert materia_b not in materias
        # materia_id NULL excluido cuando hay scope de materias
        assert None not in materias


# ── 3.6 Verificar solo lectura ────────────────────────────────────────────────


class TestSoloLectura:
    """Verifica que AuditoriaRepository no expone create/update/delete sobre AuditLog."""

    def test_no_tiene_create(self):
        from app.repositories.auditoria_repository import AuditoriaRepository
        assert not hasattr(AuditoriaRepository, "create")
        assert not hasattr(AuditoriaRepository, "create_entry")

    def test_no_tiene_update(self):
        from app.repositories.auditoria_repository import AuditoriaRepository
        assert not hasattr(AuditoriaRepository, "update")

    def test_no_tiene_delete(self):
        from app.repositories.auditoria_repository import AuditoriaRepository
        assert not hasattr(AuditoriaRepository, "delete")
        assert not hasattr(AuditoriaRepository, "soft_delete")
