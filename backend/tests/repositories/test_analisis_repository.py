"""Tests de integración para AnalisisRepository (C-11, Tarea 3.4).

Usa SQLite in-memory para aislamiento sin PG real.
Valida: scope por asignacion, scope por materia, get_umbral con fallback.

Nota: algunas FKs (materia_id en Asignacion → materia.id) requieren
insertar la entidad Materia antes de la Asignacion.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
from app.models.tenant import Tenant
import app.models  # noqa: F401 — registra todos los modelos en Base.metadata


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


@pytest.fixture
async def tenant(db):
    from app.models.tenant import Tenant
    t = Tenant(id=uuid.uuid4(), name="Tenant Principal")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
async def other_tenant(db):
    from app.models.tenant import Tenant
    t = Tenant(id=uuid.uuid4(), name="Otro Tenant")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
async def materia(db, tenant):
    """Crea una Materia para satisfacer FK en Asignacion."""
    from app.models.estructura import Materia, EstadoEntidad
    m = Materia(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nombre="Programación",
        codigo="PROG101",
        estado=EstadoEntidad.activa,
    )
    db.add(m)
    await db.commit()
    return m


@pytest.fixture
async def carrera(db, tenant):
    """Crea una Carrera para satisfacer FK en Cohorte."""
    from app.models.estructura import Carrera, EstadoEntidad
    c = Carrera(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nombre="Ingeniería",
        codigo="ING",
        estado=EstadoEntidad.activa,
    )
    db.add(c)
    await db.commit()
    return c


@pytest.fixture
async def cohorte(db, tenant, carrera):
    """Crea una Cohorte para VersionPadron."""
    from app.models.estructura import Cohorte, EstadoEntidad
    from datetime import date
    c = Cohorte(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        carrera_id=carrera.id,
        nombre="2024",
        anio=2024,
        vig_desde=date(2024, 1, 1),
        estado=EstadoEntidad.activa,
    )
    db.add(c)
    await db.commit()
    return c


@pytest.fixture
async def user(db, tenant):
    """Crea un usuario mínimo para Asignacion.usuario_id."""
    from app.models.user import User
    from app.models.estructura import EstadoEntidad
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="prof@test.com",
        password_hash="hashed",
        is_active=True,
        estado=EstadoEntidad.activa,
    )
    db.add(u)
    await db.commit()
    return u


@pytest.fixture
async def asignacion(db, tenant, user, materia, cohorte):
    """Crea una Asignacion activa para el usuario."""
    from app.models.asignacion import Asignacion, RolDominio
    a = Asignacion(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        usuario_id=user.id,
        rol=RolDominio.PROFESOR,
        materia_id=materia.id,
        cohorte_id=cohorte.id,
        desde=date(2024, 1, 1),
        hasta=None,
    )
    db.add(a)
    await db.commit()
    return a


@pytest.fixture
async def version_padron(db, tenant, materia, cohorte):
    """Crea una VersionPadron activa."""
    from app.models.padron import VersionPadron
    vp = VersionPadron(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        materia_id=materia.id,
        cohorte_id=cohorte.id,
        activa=True,
    )
    db.add(vp)
    await db.commit()
    return vp


@pytest.fixture
async def entrada_padron(db, tenant, version_padron):
    """Crea una EntradaPadron."""
    from app.models.padron import EntradaPadron
    ep = EntradaPadron(
        id=uuid.uuid4(),
        version_id=version_padron.id,
        tenant_id=tenant.id,
        nombre="Juan",
        apellidos="Pérez",
        email_enc="ENC_EMAIL",
        comision="COM-A",
    )
    db.add(ep)
    await db.commit()
    return ep


@pytest.fixture
async def calificacion(db, tenant, materia, entrada_padron):
    """Crea una Calificacion para el alumno."""
    from app.models.calificacion import Calificacion, OrigenCalificacion
    c = Calificacion(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        entrada_padron_id=entrada_padron.id,
        materia_id=materia.id,
        actividad="TP1",
        nota_numerica=8.0,
        nota_textual=None,
        origen=OrigenCalificacion.IMPORTADO,
    )
    db.add(c)
    await db.commit()
    return c


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestGetCalificacionesPorAsignacion:
    async def test_retorna_alumno_del_scope_correcto(
        self, db, tenant, asignacion, entrada_padron, calificacion, materia
    ):
        """get_calificaciones_por_asignacion retorna el alumno de la asignación."""
        from app.repositories.analisis_repository import AnalisisRepository

        repo = AnalisisRepository(db)
        result = await repo.get_calificaciones_por_asignacion(
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            tenant_id=tenant.id,
            cipher=None,
        )
        assert len(result) == 1
        assert result[0].nombre == "Juan"
        assert any(c.actividad == "TP1" for c in result[0].calificaciones)

    async def test_asignacion_inexistente_retorna_vacia(self, db, tenant, materia):
        """Si la asignacion_id no existe → lista vacía."""
        from app.repositories.analisis_repository import AnalisisRepository

        repo = AnalisisRepository(db)
        result = await repo.get_calificaciones_por_asignacion(
            asignacion_id=uuid.uuid4(),
            materia_id=materia.id,
            tenant_id=tenant.id,
        )
        assert result == []

    async def test_scope_isolation_otro_tenant_no_accede(
        self, db, other_tenant, tenant, asignacion, materia
    ):
        """Asignación del tenant correcto pero consultando con otro tenant_id → vacío."""
        from app.repositories.analisis_repository import AnalisisRepository

        repo = AnalisisRepository(db)
        result = await repo.get_calificaciones_por_asignacion(
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            tenant_id=other_tenant.id,  # tenant incorrecto
        )
        assert result == []


class TestGetCalificacionesPorMateria:
    async def test_retorna_todos_los_alumnos_del_tenant(
        self, db, tenant, entrada_padron, calificacion, materia
    ):
        """get_calificaciones_por_materia retorna todos los alumnos de la materia."""
        from app.repositories.analisis_repository import AnalisisRepository

        repo = AnalisisRepository(db)
        result = await repo.get_calificaciones_por_materia(
            materia_id=materia.id,
            tenant_id=tenant.id,
            cipher=None,
        )
        assert len(result) == 1
        assert result[0].nombre == "Juan"

    async def test_materia_sin_padron_retorna_vacia(self, db, tenant):
        """Materia sin versión padrón activa → lista vacía."""
        from app.repositories.analisis_repository import AnalisisRepository

        repo = AnalisisRepository(db)
        result = await repo.get_calificaciones_por_materia(
            materia_id=uuid.uuid4(),
            tenant_id=tenant.id,
        )
        assert result == []

    async def test_otro_tenant_no_accede(self, db, other_tenant, materia):
        """Otro tenant no puede ver los datos de la materia."""
        from app.repositories.analisis_repository import AnalisisRepository

        repo = AnalisisRepository(db)
        result = await repo.get_calificaciones_por_materia(
            materia_id=materia.id,
            tenant_id=other_tenant.id,
        )
        assert result == []


class TestGetUmbral:
    async def test_umbral_existente_retorna_configurado(
        self, db, tenant, asignacion, materia
    ):
        """Si existe UmbralMateria → retorna el umbral configurado."""
        from app.models.calificacion import UmbralMateria
        from app.repositories.analisis_repository import AnalisisRepository

        um = UmbralMateria(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=75,
            valores_aprobatorios=["Aprobado"],
        )
        db.add(um)
        await db.commit()

        repo = AnalisisRepository(db)
        result = await repo.get_umbral(
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            tenant_id=tenant.id,
        )
        assert result.umbral_pct == 75
        assert result.valores_aprobatorios == ["Aprobado"]

    async def test_umbral_inexistente_retorna_defecto_60(
        self, db, tenant, materia
    ):
        """Si no existe UmbralMateria → fallback a 60%."""
        from app.repositories.analisis_repository import AnalisisRepository

        repo = AnalisisRepository(db)
        result = await repo.get_umbral(
            asignacion_id=uuid.uuid4(),
            materia_id=materia.id,
            tenant_id=tenant.id,
        )
        assert result.umbral_pct == 60
        assert result.valores_aprobatorios == []
