"""Tests para PadronRepository y MoodleConfigRepository.

TDD — usa SQLite in-memory (aiosqlite) para aislamiento sin PG real.
"""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
from app.models.tenant import Tenant
import app.models  # noqa: F401 — registra todos los modelos


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
    t = Tenant(id=uuid.uuid4(), name="Tenant Test")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
async def other_tenant(db):
    t = Tenant(id=uuid.uuid4(), name="Other Tenant")
    db.add(t)
    await db.commit()
    return t


# ── PadronRepository ──────────────────────────────────────────────────────────


class TestPadronRepositoryGetActiva:
    async def test_get_activa_returns_none_when_no_version(self, db, tenant):
        from app.repositories.padron_repository import PadronRepository

        repo = PadronRepository(db)
        materia_id = uuid.uuid4()
        cohorte_id = uuid.uuid4()

        result = await repo.get_activa(materia_id, cohorte_id, tenant.id)
        assert result is None

    async def test_get_activa_returns_active_version(self, db, tenant):
        from app.models.padron import VersionPadron
        from app.repositories.padron_repository import PadronRepository

        materia_id = uuid.uuid4()
        cohorte_id = uuid.uuid4()

        vp = VersionPadron(
            tenant_id=tenant.id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=uuid.uuid4(),
            activa=True,
        )
        db.add(vp)
        await db.commit()

        repo = PadronRepository(db)
        result = await repo.get_activa(materia_id, cohorte_id, tenant.id)
        assert result is not None
        assert result.id == vp.id

    async def test_get_activa_respects_tenant_isolation(self, db, tenant, other_tenant):
        from app.models.padron import VersionPadron
        from app.repositories.padron_repository import PadronRepository

        materia_id = uuid.uuid4()
        cohorte_id = uuid.uuid4()

        # Crear versión en other_tenant
        vp = VersionPadron(
            tenant_id=other_tenant.id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=uuid.uuid4(),
            activa=True,
        )
        db.add(vp)
        await db.commit()

        repo = PadronRepository(db)
        result = await repo.get_activa(materia_id, cohorte_id, tenant.id)
        # No debe ver versión de otro tenant
        assert result is None


class TestPadronRepositoryCrearVersionConEntradas:
    async def test_crear_version_con_entradas_atomico(self, db, tenant):
        from app.models.padron import EntradaPadron, VersionPadron
        from app.repositories.padron_repository import PadronRepository

        materia_id = uuid.uuid4()
        cohorte_id = uuid.uuid4()
        user_id = uuid.uuid4()

        version = VersionPadron(
            tenant_id=tenant.id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=user_id,
            activa=True,
        )
        entradas = [
            EntradaPadron(
                tenant_id=tenant.id,
                nombre="Juan",
                apellidos="Pérez",
                email_enc="ENC1",
            ),
            EntradaPadron(
                tenant_id=tenant.id,
                nombre="María",
                apellidos="García",
                email_enc="ENC2",
            ),
        ]

        repo = PadronRepository(db)
        saved_version = await repo.crear_version_con_entradas(version, entradas)

        assert saved_version.id is not None
        # Verificar entradas persistidas con la FK correcta
        from sqlalchemy import select
        from app.models.padron import EntradaPadron as EP

        result = await db.execute(
            select(EP).where(EP.version_id == saved_version.id)
        )
        saved_entradas = result.scalars().all()
        assert len(saved_entradas) == 2

    async def test_crear_version_desactiva_anterior(self, db, tenant):
        from app.models.padron import VersionPadron
        from app.repositories.padron_repository import PadronRepository

        materia_id = uuid.uuid4()
        cohorte_id = uuid.uuid4()

        # Primera versión activa
        old_version = VersionPadron(
            tenant_id=tenant.id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=uuid.uuid4(),
            activa=True,
        )
        db.add(old_version)
        await db.commit()

        # Segunda versión — debe desactivar la primera
        new_version = VersionPadron(
            tenant_id=tenant.id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=uuid.uuid4(),
            activa=True,
        )

        repo = PadronRepository(db)
        saved = await repo.crear_version_con_entradas(new_version, [])

        await db.refresh(old_version)
        assert old_version.activa is False
        assert saved.activa is True


class TestPadronRepositoryListarVersiones:
    async def test_listar_versiones_returns_all(self, db, tenant):
        from app.models.padron import VersionPadron
        from app.repositories.padron_repository import PadronRepository

        materia_id = uuid.uuid4()
        cohorte_id = uuid.uuid4()

        for i in range(3):
            vp = VersionPadron(
                tenant_id=tenant.id,
                materia_id=materia_id,
                cohorte_id=cohorte_id,
                cargado_por=uuid.uuid4(),
                activa=(i == 2),
            )
            db.add(vp)
        await db.commit()

        repo = PadronRepository(db)
        versions = await repo.listar_versiones(materia_id, tenant.id)
        assert len(versions) == 3

    async def test_listar_versiones_tenant_isolated(self, db, tenant, other_tenant):
        from app.models.padron import VersionPadron
        from app.repositories.padron_repository import PadronRepository

        materia_id = uuid.uuid4()
        cohorte_id = uuid.uuid4()

        # Versión en tenant
        db.add(VersionPadron(
            tenant_id=tenant.id, materia_id=materia_id,
            cohorte_id=cohorte_id, cargado_por=uuid.uuid4(), activa=True,
        ))
        # Versión en other_tenant (misma materia)
        db.add(VersionPadron(
            tenant_id=other_tenant.id, materia_id=materia_id,
            cohorte_id=cohorte_id, cargado_por=uuid.uuid4(), activa=True,
        ))
        await db.commit()

        repo = PadronRepository(db)
        versions = await repo.listar_versiones(materia_id, tenant.id)
        assert len(versions) == 1


# ── MoodleConfigRepository ────────────────────────────────────────────────────


class TestMoodleConfigRepository:
    async def test_get_by_tenant_returns_none_when_not_configured(self, db, tenant):
        from app.repositories.moodle_config_repository import MoodleConfigRepository

        repo = MoodleConfigRepository(db)
        result = await repo.get_by_tenant(tenant.id)
        assert result is None

    async def test_upsert_creates_config(self, db, tenant):
        from app.models.tenant_moodle_config import TenantMoodleConfig
        from app.repositories.moodle_config_repository import MoodleConfigRepository

        config = TenantMoodleConfig(
            tenant_id=tenant.id,
            moodle_url_enc="URL_ENC",
            moodle_token_enc="TOKEN_ENC",
        )

        repo = MoodleConfigRepository(db)
        saved = await repo.upsert(config, tenant.id)

        assert saved.id is not None
        assert saved.moodle_url_enc == "URL_ENC"

    async def test_upsert_replaces_existing_config(self, db, tenant):
        from app.models.tenant_moodle_config import TenantMoodleConfig
        from app.repositories.moodle_config_repository import MoodleConfigRepository

        repo = MoodleConfigRepository(db)

        config1 = TenantMoodleConfig(
            tenant_id=tenant.id,
            moodle_url_enc="OLD_URL",
            moodle_token_enc="OLD_TOKEN",
        )
        await repo.upsert(config1, tenant.id)

        config2 = TenantMoodleConfig(
            tenant_id=tenant.id,
            moodle_url_enc="NEW_URL",
            moodle_token_enc="NEW_TOKEN",
        )
        saved = await repo.upsert(config2, tenant.id)

        # Solo debe haber una entrada
        from sqlalchemy import select
        from app.models.tenant_moodle_config import TenantMoodleConfig as TMC
        result = await db.execute(select(TMC).where(TMC.tenant_id == tenant.id))
        all_configs = result.scalars().all()
        assert len(all_configs) == 1
        assert saved.moodle_url_enc == "NEW_URL"
