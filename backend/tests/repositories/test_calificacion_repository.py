"""Tests para CalificacionRepository y UmbralRepository (C-10).

TDD — usa SQLite in-memory (aiosqlite) para aislamiento sin PG real.
Valida: filtro tenant por defecto, soft delete, aislamiento entre tenants, upsert de umbral.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
from app.models.tenant import Tenant
import app.models  # noqa: F401 — registra todos los modelos incluyendo calificacion


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
    t = Tenant(id=uuid.uuid4(), name="Tenant Principal")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
async def other_tenant(db):
    t = Tenant(id=uuid.uuid4(), name="Otro Tenant")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
async def entrada_padron(db, tenant):
    """Crea una EntradaPadron mínima para usar como FK en Calificacion."""
    from app.models.padron import EntradaPadron, VersionPadron

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        cargado_por=uuid.uuid4(),
        activa=True,
    )
    db.add(vp)
    await db.flush()

    ep = EntradaPadron(
        version_id=vp.id,
        tenant_id=tenant.id,
        nombre="Alumno",
        apellidos="Test",
        email_enc="ENC",
    )
    db.add(ep)
    await db.commit()
    return ep


@pytest.fixture
async def entrada_other_tenant(db, other_tenant):
    """EntradaPadron del otro tenant."""
    from app.models.padron import EntradaPadron, VersionPadron

    vp = VersionPadron(
        tenant_id=other_tenant.id,
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        cargado_por=uuid.uuid4(),
        activa=True,
    )
    db.add(vp)
    await db.flush()

    ep = EntradaPadron(
        version_id=vp.id,
        tenant_id=other_tenant.id,
        nombre="Otro",
        apellidos="Alumno",
        email_enc="ENC_OTHER",
    )
    db.add(ep)
    await db.commit()
    return ep


# ── CalificacionRepository ────────────────────────────────────────────────────


class TestCalificacionRepository:
    async def test_crear_calificacion_y_listar_por_tenant(self, db, tenant, entrada_padron):
        """Una calificación creada se lista correctamente filtrada por tenant."""
        from app.models.calificacion import Calificacion, OrigenCalificacion
        from app.repositories.calificacion_repository import CalificacionRepository

        materia_id = uuid.uuid4()
        cal = Calificacion(
            entrada_padron_id=entrada_padron.id,
            materia_id=materia_id,
            actividad="TP1",
            nota_numerica=8.0,
            origen=OrigenCalificacion.IMPORTADO,
            importado_at=datetime.now(timezone.utc),
            tenant_id=tenant.id,
        )

        repo = CalificacionRepository(db)
        saved = await repo.crear(cal)
        assert saved.id is not None

        lista = await repo.listar_por_materia(materia_id, tenant.id)
        assert len(lista) == 1
        assert lista[0].id == saved.id

    async def test_listar_excluye_soft_deleted(self, db, tenant, entrada_padron):
        """Registros con deleted_at no nulo no aparecen en el listado."""
        from app.models.calificacion import Calificacion, OrigenCalificacion
        from app.repositories.calificacion_repository import CalificacionRepository

        materia_id = uuid.uuid4()
        cal = Calificacion(
            entrada_padron_id=entrada_padron.id,
            materia_id=materia_id,
            actividad="TP2",
            nota_numerica=9.0,
            origen=OrigenCalificacion.IMPORTADO,
            importado_at=datetime.now(timezone.utc),
            tenant_id=tenant.id,
            deleted_at=datetime.now(timezone.utc),
        )
        db.add(cal)
        await db.commit()

        repo = CalificacionRepository(db)
        lista = await repo.listar_por_materia(materia_id, tenant.id)
        assert len(lista) == 0

    async def test_aislamiento_entre_tenants(self, db, tenant, other_tenant, entrada_padron, entrada_other_tenant):
        """Calificaciones de un tenant no son visibles desde otro."""
        from app.models.calificacion import Calificacion, OrigenCalificacion
        from app.repositories.calificacion_repository import CalificacionRepository

        materia_id = uuid.uuid4()

        cal_tenant = Calificacion(
            entrada_padron_id=entrada_padron.id,
            materia_id=materia_id,
            actividad="TP3",
            nota_numerica=7.0,
            origen=OrigenCalificacion.IMPORTADO,
            importado_at=datetime.now(timezone.utc),
            tenant_id=tenant.id,
        )
        cal_other = Calificacion(
            entrada_padron_id=entrada_other_tenant.id,
            materia_id=materia_id,
            actividad="TP3",
            nota_numerica=5.0,
            origen=OrigenCalificacion.IMPORTADO,
            importado_at=datetime.now(timezone.utc),
            tenant_id=other_tenant.id,
        )
        db.add(cal_tenant)
        db.add(cal_other)
        await db.commit()

        repo = CalificacionRepository(db)
        lista_tenant = await repo.listar_por_materia(materia_id, tenant.id)
        lista_other = await repo.listar_por_materia(materia_id, other_tenant.id)

        assert len(lista_tenant) == 1
        assert lista_tenant[0].nota_numerica == 7.0
        assert len(lista_other) == 1
        assert lista_other[0].nota_numerica == 5.0

    async def test_listar_por_entrada_padron(self, db, tenant, entrada_padron):
        """Listar calificaciones de un alumno específico."""
        from app.models.calificacion import Calificacion, OrigenCalificacion
        from app.repositories.calificacion_repository import CalificacionRepository

        materia_id = uuid.uuid4()
        for actividad in ["TP1", "TP2", "Parcial"]:
            db.add(Calificacion(
                entrada_padron_id=entrada_padron.id,
                materia_id=materia_id,
                actividad=actividad,
                nota_numerica=7.0,
                origen=OrigenCalificacion.IMPORTADO,
                importado_at=datetime.now(timezone.utc),
                tenant_id=tenant.id,
            ))
        await db.commit()

        repo = CalificacionRepository(db)
        lista = await repo.listar_por_entrada(entrada_padron.id, tenant.id)
        assert len(lista) == 3

    async def test_bulk_crear_calificaciones(self, db, tenant, entrada_padron):
        """Inserción masiva de calificaciones."""
        from app.models.calificacion import Calificacion, OrigenCalificacion
        from app.repositories.calificacion_repository import CalificacionRepository

        materia_id = uuid.uuid4()
        cals = [
            Calificacion(
                entrada_padron_id=entrada_padron.id,
                materia_id=materia_id,
                actividad=f"Act{i}",
                nota_numerica=float(i),
                origen=OrigenCalificacion.IMPORTADO,
                importado_at=datetime.now(timezone.utc),
                tenant_id=tenant.id,
            )
            for i in range(5)
        ]

        repo = CalificacionRepository(db)
        count = await repo.bulk_crear(cals)
        assert count == 5

        lista = await repo.listar_por_materia(materia_id, tenant.id)
        assert len(lista) == 5


# ── UmbralRepository ──────────────────────────────────────────────────────────


class TestUmbralRepository:
    async def test_get_by_asignacion_materia_returns_none_when_not_exists(self, db, tenant):
        """Retorna None si no hay umbral configurado."""
        from app.repositories.umbral_repository import UmbralRepository

        repo = UmbralRepository(db)
        result = await repo.get_by_asignacion_materia(
            tenant_id=tenant.id,
            asignacion_id=uuid.uuid4(),
            materia_id=uuid.uuid4(),
        )
        assert result is None

    async def test_upsert_crea_umbral(self, db, tenant):
        """Upsert crea un UmbralMateria cuando no existe."""
        from app.models.calificacion import UmbralMateria
        from app.repositories.umbral_repository import UmbralRepository

        asignacion_id = uuid.uuid4()
        materia_id = uuid.uuid4()

        um = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=70,
            valores_aprobatorios=["Satisfactorio"],
        )

        repo = UmbralRepository(db)
        saved = await repo.upsert(um, tenant.id)
        assert saved.id is not None
        assert saved.umbral_pct == 70

    async def test_upsert_actualiza_umbral_existente(self, db, tenant):
        """Upsert actualiza el umbral cuando ya existe para (tenant, asignacion, materia)."""
        from app.models.calificacion import UmbralMateria
        from app.repositories.umbral_repository import UmbralRepository

        asignacion_id = uuid.uuid4()
        materia_id = uuid.uuid4()

        repo = UmbralRepository(db)

        # Primera inserción
        um1 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=60,
            valores_aprobatorios=[],
        )
        await repo.upsert(um1, tenant.id)

        # Segunda inserción — debería actualizar, no duplicar
        um2 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=80,
            valores_aprobatorios=["A", "B"],
        )
        updated = await repo.upsert(um2, tenant.id)
        assert updated.umbral_pct == 80

        # Solo debe existir un registro
        result = await repo.get_by_asignacion_materia(tenant.id, asignacion_id, materia_id)
        assert result is not None
        assert result.umbral_pct == 80

    async def test_aislamiento_entre_docentes(self, db, tenant):
        """El umbral de un docente no afecta al de otro."""
        from app.models.calificacion import UmbralMateria
        from app.repositories.umbral_repository import UmbralRepository

        materia_id = uuid.uuid4()
        asignacion_a = uuid.uuid4()
        asignacion_b = uuid.uuid4()

        repo = UmbralRepository(db)

        await repo.upsert(UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion_a,
            materia_id=materia_id,
            umbral_pct=60,
            valores_aprobatorios=[],
        ), tenant.id)

        await repo.upsert(UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion_b,
            materia_id=materia_id,
            umbral_pct=90,
            valores_aprobatorios=["A"],
        ), tenant.id)

        # Cambiar umbral de A no toca B
        await repo.upsert(UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion_a,
            materia_id=materia_id,
            umbral_pct=75,
            valores_aprobatorios=[],
        ), tenant.id)

        um_a = await repo.get_by_asignacion_materia(tenant.id, asignacion_a, materia_id)
        um_b = await repo.get_by_asignacion_materia(tenant.id, asignacion_b, materia_id)

        assert um_a.umbral_pct == 75
        assert um_b.umbral_pct == 90  # sin cambios
