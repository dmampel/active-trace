"""Tests TDD para UmbralService (C-10 — Tareas 6.1–6.6).

Valida:
- configurar() persiste UmbralMateria para la asignación del docente
- resolver_umbral() usa el UmbralMateria de la asignación; defecto 60% si no existe
- aislamiento: cambiar umbral de docente A no afecta docente B
- derivar_aprobado integrado: el service usa la función pura con el umbral resuelto
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
from app.models.tenant import Tenant
import app.models  # noqa: F401


# ── Fixtures ──────────────────────────────────────────────────────────────────


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


@pytest.fixture
async def tenant(db):
    t = Tenant(id=uuid.uuid4(), name="Tenant Umbral")
    db.add(t)
    await db.commit()
    return t


# ── UmbralService.configurar ──────────────────────────────────────────────────


class TestUmbralServiceConfigurar:
    async def test_configurar_persiste_umbral_para_asignacion(self, db, tenant):
        """configurar() crea UmbralMateria para la asignación del docente (toma tenant del JWT)."""
        from app.repositories.umbral_repository import UmbralRepository
        from app.services.umbral_service import UmbralService

        repo = UmbralRepository(db)
        service = UmbralService(repo)

        asignacion_id = uuid.uuid4()
        materia_id = uuid.uuid4()

        saved = await service.configurar(
            tenant_id=tenant.id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=70,
            valores_aprobatorios=["Satisfactorio", "Supera lo esperado"],
        )

        assert saved.id is not None
        assert saved.umbral_pct == 70
        assert saved.asignacion_id == asignacion_id
        assert saved.tenant_id == tenant.id

    async def test_configurar_actualiza_umbral_existente(self, db, tenant):
        """configurar() hace upsert — no duplica el umbral."""
        from app.repositories.umbral_repository import UmbralRepository
        from app.services.umbral_service import UmbralService

        repo = UmbralRepository(db)
        service = UmbralService(repo)

        asignacion_id = uuid.uuid4()
        materia_id = uuid.uuid4()

        await service.configurar(
            tenant_id=tenant.id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=60,
            valores_aprobatorios=[],
        )
        updated = await service.configurar(
            tenant_id=tenant.id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=80,
            valores_aprobatorios=["A"],
        )

        assert updated.umbral_pct == 80
        # Verificar que no se duplicó
        fetched = await repo.get_by_asignacion_materia(tenant.id, asignacion_id, materia_id)
        assert fetched.umbral_pct == 80


# ── UmbralService.resolver_umbral ─────────────────────────────────────────────


class TestUmbralServiceResolver:
    async def test_resolver_usa_umbral_de_asignacion(self, db, tenant):
        """resolver_umbral() retorna el umbral configurado para la asignación."""
        from app.repositories.umbral_repository import UmbralRepository
        from app.services.umbral_service import UmbralService

        repo = UmbralRepository(db)
        service = UmbralService(repo)

        asignacion_id = uuid.uuid4()
        materia_id = uuid.uuid4()

        await service.configurar(
            tenant_id=tenant.id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=75,
            valores_aprobatorios=["Satisfactorio"],
        )

        pct, valores = await service.resolver_umbral(tenant.id, asignacion_id, materia_id)
        assert pct == 75
        assert "Satisfactorio" in valores

    async def test_resolver_retorna_defecto_60_cuando_no_existe(self, db, tenant):
        """Sin UmbralMateria configurado → defecto del tenant = 60%."""
        from app.repositories.umbral_repository import UmbralRepository
        from app.services.umbral_service import UmbralService

        repo = UmbralRepository(db)
        service = UmbralService(repo)

        pct, valores = await service.resolver_umbral(tenant.id, uuid.uuid4(), uuid.uuid4())
        assert pct == 60
        assert valores == []

    async def test_aislamiento_entre_docentes(self, db, tenant):
        """Cambiar umbral del docente A no afecta al docente B."""
        from app.repositories.umbral_repository import UmbralRepository
        from app.services.umbral_service import UmbralService

        repo = UmbralRepository(db)
        service = UmbralService(repo)

        materia_id = uuid.uuid4()
        asig_a = uuid.uuid4()
        asig_b = uuid.uuid4()

        await service.configurar(tenant.id, asig_a, materia_id, 60, [])
        await service.configurar(tenant.id, asig_b, materia_id, 90, ["A"])

        # Cambiar umbral de A
        await service.configurar(tenant.id, asig_a, materia_id, 75, [])

        pct_a, _ = await service.resolver_umbral(tenant.id, asig_a, materia_id)
        pct_b, _ = await service.resolver_umbral(tenant.id, asig_b, materia_id)

        assert pct_a == 75
        assert pct_b == 90  # sin cambios


# ── Integración derivar_aprobado ──────────────────────────────────────────────


class TestUmbralServiceDerivarAprobado:
    async def test_derivar_usa_umbral_de_asignacion(self, db, tenant):
        """El service resuelve el umbral y llama derivar_aprobado."""
        from app.repositories.umbral_repository import UmbralRepository
        from app.services.umbral_service import UmbralService

        repo = UmbralRepository(db)
        service = UmbralService(repo)

        asig_id = uuid.uuid4()
        materia_id = uuid.uuid4()

        await service.configurar(tenant.id, asig_id, materia_id, 80, [])

        # 7/10 con umbral 80% → false
        aprobado = await service.derivar_aprobado_para(
            tenant_id=tenant.id,
            asignacion_id=asig_id,
            materia_id=materia_id,
            nota_numerica=7.0,
            nota_textual=None,
            nota_maxima=10.0,
        )
        assert aprobado is False

    async def test_derivar_usa_defecto_cuando_no_hay_umbral(self, db, tenant):
        """Sin umbral configurado, usa 60% (defecto)."""
        from app.repositories.umbral_repository import UmbralRepository
        from app.services.umbral_service import UmbralService

        repo = UmbralRepository(db)
        service = UmbralService(repo)

        # 7/10 con defecto 60% → true
        aprobado = await service.derivar_aprobado_para(
            tenant_id=tenant.id,
            asignacion_id=uuid.uuid4(),
            materia_id=uuid.uuid4(),
            nota_numerica=7.0,
            nota_textual=None,
            nota_maxima=10.0,
        )
        assert aprobado is True
