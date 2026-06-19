"""Tests para AuditoriaService (C-19, Tareas 4.1–4.4).

Usa SQLite in-memory + mocks de CurrentUser.
Valida:
- 4.1 Resolución de scope: ADMIN/FINANZAS sin restricción, COORDINADOR solo sus materias.
- 4.2 Casos borde de scope: sin materias, materia ajena, materia_id NULL.
- 4.3 Clamp del límite de últimas acciones.
- 4.4 Métodos wrapper que aplican scope y devuelven DTOs.

TDD — RED+GREEN+TRIANGULATE por cada regla de negocio.
"""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

# Env vars requeridas por Settings antes de importar la app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
import app.models  # noqa: F401

from app.core.dependencies import CurrentUser


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


def _make_current_user(roles: list[str], tenant_id: uuid.UUID | None = None, user_id: uuid.UUID | None = None) -> CurrentUser:
    user = MagicMock(spec=CurrentUser)
    user.id = user_id or uuid.uuid4()
    user.tenant_id = tenant_id or uuid.uuid4()
    user.roles = roles
    user.impersonado_id = None
    return user


async def _make_tenant(db: AsyncSession, name: str = "T") -> uuid.UUID:
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


def _make_asignacion(materia_id: uuid.UUID, rol: str = "COORDINADOR"):
    """Mock de asignación vigente con materia_id y rol."""
    asig = MagicMock()
    asig.materia_id = materia_id
    asig.rol = rol
    return asig


# ── 4.1 Resolución de scope ───────────────────────────────────────────────────


class TestScopeResolucion:
    """ADMIN/FINANZAS sin restricción; COORDINADOR solo sus materias."""

    async def test_admin_obtiene_scope_global(self, db):
        """ADMIN → materia_ids=None (sin restricción)."""
        from app.services.auditoria_service import AuditoriaService
        from app.repositories.auditoria_repository import AuditoriaRepository
        from app.repositories.asignacion_repository import AsignacionRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_a = uuid.uuid4()
        materia_b = uuid.uuid4()
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_a)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_b)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=None)  # global

        svc = AuditoriaService(
            auditoria_repo=AuditoriaRepository(db),
            asignacion_repo=AsignacionRepository(db),
        )
        current_user = _make_current_user(roles=["ADMIN"], tenant_id=tenant_id)
        result = await svc.get_log(current_user=current_user)

        # ADMIN ve todos (materia_a, materia_b, NULL)
        assert result.total >= 3

    async def test_finanzas_obtiene_scope_global(self, db):
        """FINANZAS → igual que ADMIN, sin restricción de materia."""
        from app.services.auditoria_service import AuditoriaService
        from app.repositories.auditoria_repository import AuditoriaRepository
        from app.repositories.asignacion_repository import AsignacionRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_a = uuid.uuid4()
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_a)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=None)

        svc = AuditoriaService(
            auditoria_repo=AuditoriaRepository(db),
            asignacion_repo=AsignacionRepository(db),
        )
        current_user = _make_current_user(roles=["FINANZAS"], tenant_id=tenant_id)
        result = await svc.get_log(current_user=current_user)

        assert result.total >= 2

    async def test_coordinador_ve_solo_sus_materias(self, db):
        """COORDINADOR (no ADMIN) → solo materias de sus asignaciones vigentes."""
        from app.services.auditoria_service import AuditoriaService
        from app.repositories.auditoria_repository import AuditoriaRepository
        from app.repositories.asignacion_repository import AsignacionRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_coord = uuid.uuid4()
        materia_otra = uuid.uuid4()

        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_coord)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_otra)

        # Mock del AsignacionRepository para devolver la asignación del coordinador
        asig_repo_mock = MagicMock()
        asig_coord = _make_asignacion(materia_id=materia_coord, rol="COORDINADOR")
        asig_repo_mock.list_vigentes = AsyncMock(return_value=[asig_coord])

        svc = AuditoriaService(
            auditoria_repo=AuditoriaRepository(db),
            asignacion_repo=asig_repo_mock,
        )
        current_user = _make_current_user(roles=["COORDINADOR"], tenant_id=tenant_id)
        result = await svc.get_log(current_user=current_user)

        materias = {item.materia_id for item in result.items}
        assert materia_coord in materias
        assert materia_otra not in materias


# ── 4.2 Casos borde de scope ──────────────────────────────────────────────────


class TestScopeBorde:
    """Coordinador sin materias, materia ajena, materia_id NULL."""

    async def test_coordinador_sin_materias_resultado_vacio(self, db):
        """COORDINADOR sin asignaciones → sin resultados con materia."""
        from app.services.auditoria_service import AuditoriaService
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_id = uuid.uuid4()
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_id)

        asig_repo_mock = MagicMock()
        asig_repo_mock.list_vigentes = AsyncMock(return_value=[])

        svc = AuditoriaService(
            auditoria_repo=AuditoriaRepository(db),
            asignacion_repo=asig_repo_mock,
        )
        current_user = _make_current_user(roles=["COORDINADOR"], tenant_id=tenant_id)
        result = await svc.get_log(current_user=current_user)

        assert result.total == 0

    async def test_filtro_a_materia_ajena_resultado_vacio(self, db):
        """COORDINADOR con scope M1 + filtro explícito M2 → intersección vacía."""
        from app.services.auditoria_service import AuditoriaService
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_coord = uuid.uuid4()
        materia_ajena = uuid.uuid4()
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_coord)

        asig_repo_mock = MagicMock()
        asig_repo_mock.list_vigentes = AsyncMock(
            return_value=[_make_asignacion(materia_id=materia_coord)]
        )

        svc = AuditoriaService(
            auditoria_repo=AuditoriaRepository(db),
            asignacion_repo=asig_repo_mock,
        )
        current_user = _make_current_user(roles=["COORDINADOR"], tenant_id=tenant_id)
        result = await svc.get_log(current_user=current_user, materia_id=materia_ajena)

        assert result.total == 0

    async def test_admin_ve_registros_con_materia_null(self, db):
        """ADMIN ve registros con materia_id=NULL (acciones globales)."""
        from app.services.auditoria_service import AuditoriaService
        from app.repositories.auditoria_repository import AuditoriaRepository
        from app.repositories.asignacion_repository import AsignacionRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=None)

        svc = AuditoriaService(
            auditoria_repo=AuditoriaRepository(db),
            asignacion_repo=AsignacionRepository(db),
        )
        current_user = _make_current_user(roles=["ADMIN"], tenant_id=tenant_id)
        result = await svc.get_log(current_user=current_user)

        null_materia = [item for item in result.items if item.materia_id is None]
        assert len(null_materia) >= 1

    async def test_coordinador_no_ve_registros_con_materia_null(self, db):
        """COORDINADOR NO ve registros con materia_id=NULL."""
        from app.services.auditoria_service import AuditoriaService
        from app.repositories.auditoria_repository import AuditoriaRepository

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_coord = uuid.uuid4()
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_coord)
        await _make_audit_log(db, tenant_id, actor_id, materia_id=None)  # global — NO visible

        asig_repo_mock = MagicMock()
        asig_repo_mock.list_vigentes = AsyncMock(
            return_value=[_make_asignacion(materia_id=materia_coord)]
        )

        svc = AuditoriaService(
            auditoria_repo=AuditoriaRepository(db),
            asignacion_repo=asig_repo_mock,
        )
        current_user = _make_current_user(roles=["COORDINADOR"], tenant_id=tenant_id)
        result = await svc.get_log(current_user=current_user)

        null_materia = [item for item in result.items if item.materia_id is None]
        assert len(null_materia) == 0


# ── 4.3 Clamp del límite ─────────────────────────────────────────────────────


class TestClampLimite:
    """limite <= 0 → default; limite > max → max; limite válido respetado."""

    def _make_svc(self, db=None):
        from app.services.auditoria_service import AuditoriaService
        from app.core.config import Settings

        auditoria_repo = MagicMock()
        auditoria_repo.ultimas_acciones = AsyncMock(return_value=[])
        asig_repo = MagicMock()
        asig_repo.list_vigentes = AsyncMock(return_value=[])

        settings = MagicMock(spec=Settings)
        settings.auditoria_log_limite_default = 200
        settings.auditoria_log_limite_max = 1000

        return AuditoriaService(
            auditoria_repo=auditoria_repo,
            asignacion_repo=asig_repo,
            settings=settings,
        ), auditoria_repo

    async def test_limite_no_positivo_usa_default(self):
        """limite=0 → se usa 200 (default)."""
        svc, repo = self._make_svc()
        current_user = _make_current_user(roles=["ADMIN"])
        await svc.get_ultimas_acciones(current_user=current_user, limite=0)

        _, kwargs = repo.ultimas_acciones.call_args
        assert kwargs["limite"] == 200

    async def test_limite_negativo_usa_default(self):
        """limite=-5 → se usa 200 (default)."""
        svc, repo = self._make_svc()
        current_user = _make_current_user(roles=["ADMIN"])
        await svc.get_ultimas_acciones(current_user=current_user, limite=-5)

        _, kwargs = repo.ultimas_acciones.call_args
        assert kwargs["limite"] == 200

    async def test_limite_sobre_maximo_recortado(self):
        """limite=9999 > max=1000 → se usa 1000."""
        svc, repo = self._make_svc()
        current_user = _make_current_user(roles=["ADMIN"])
        await svc.get_ultimas_acciones(current_user=current_user, limite=9999)

        _, kwargs = repo.ultimas_acciones.call_args
        assert kwargs["limite"] == 1000

    async def test_limite_valido_respetado(self):
        """limite=50 (dentro del tope) → se usa 50."""
        svc, repo = self._make_svc()
        current_user = _make_current_user(roles=["ADMIN"])
        await svc.get_ultimas_acciones(current_user=current_user, limite=50)

        _, kwargs = repo.ultimas_acciones.call_args
        assert kwargs["limite"] == 50


# ── 4.4 Métodos wrapper ───────────────────────────────────────────────────────


class TestMetodosWrapper:
    """Cada método del service llama al repo con scope correcto y devuelve DTOs."""

    async def test_get_acciones_por_dia_llama_repo(self, db):
        """get_acciones_por_dia delega en el repo con tenant y scope."""
        from app.services.auditoria_service import AuditoriaService
        from app.schemas.auditoria import AccionPorDiaItem

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        dia = datetime(2026, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        await _make_audit_log(db, tenant_id, actor_id, fecha_hora=dia)

        from app.repositories.auditoria_repository import AuditoriaRepository
        from app.repositories.asignacion_repository import AsignacionRepository
        svc = AuditoriaService(
            auditoria_repo=AuditoriaRepository(db),
            asignacion_repo=AsignacionRepository(db),
        )
        current_user = _make_current_user(roles=["ADMIN"], tenant_id=tenant_id)
        result = await svc.get_acciones_por_dia(current_user=current_user)

        assert isinstance(result.items, list)
        assert all(isinstance(item, AccionPorDiaItem) for item in result.items)

    async def test_get_interacciones_llama_repo(self, db):
        """get_interacciones delega en el repo con scope correcto."""
        from app.services.auditoria_service import AuditoriaService
        from app.schemas.auditoria import InteraccionDocenteMateriaItem

        tenant_id = await _make_tenant(db)
        actor_id = await _make_user(db, tenant_id)
        materia_id = uuid.uuid4()
        await _make_audit_log(db, tenant_id, actor_id, materia_id=materia_id)

        from app.repositories.auditoria_repository import AuditoriaRepository
        from app.repositories.asignacion_repository import AsignacionRepository
        svc = AuditoriaService(
            auditoria_repo=AuditoriaRepository(db),
            asignacion_repo=AsignacionRepository(db),
        )
        current_user = _make_current_user(roles=["ADMIN"], tenant_id=tenant_id)
        result = await svc.get_interacciones(current_user=current_user)

        assert isinstance(result.items, list)
