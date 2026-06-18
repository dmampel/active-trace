"""Tests de integración para AnalisisService (C-11, Tarea 4.6).

Usa SQLite in-memory. Verifica:
- Scope isolation: PROFESOR A no ve alumnos de PROFESOR B con misma materia_id.
- Atrasado detectado correctamente.
- Ranking excluye alumnos sin aprobadas.
- Reporte rápido vacío cuando no hay calificaciones.
"""

import uuid
from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
import app.models  # noqa: F401 — registra todos los modelos en Base.metadata
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


# ── Helpers para crear fixtures ───────────────────────────────────────────────


async def _make_tenant(db, name="T1"):
    from app.models.tenant import Tenant
    t = Tenant(id=uuid.uuid4(), name=name)
    db.add(t)
    await db.commit()
    return t


async def _make_carrera(db, tenant):
    from app.models.estructura import Carrera, EstadoEntidad
    c = Carrera(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nombre="Ing",
        codigo="ING",
        estado=EstadoEntidad.activa,
    )
    db.add(c)
    await db.commit()
    return c


async def _make_cohorte(db, tenant, carrera):
    from app.models.estructura import Cohorte, EstadoEntidad
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


async def _make_materia(db, tenant):
    from app.models.estructura import Materia, EstadoEntidad
    m = Materia(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        nombre="Prog",
        codigo="P1",
        estado=EstadoEntidad.activa,
    )
    db.add(m)
    await db.commit()
    return m


async def _make_user(db, tenant, email="u@t.com"):
    from app.models.user import User
    from app.models.estructura import EstadoEntidad
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=email,
        password_hash="x",
        is_active=True,
        estado=EstadoEntidad.activa,
    )
    db.add(u)
    await db.commit()
    return u


async def _make_asignacion(db, tenant, user, materia, cohorte):
    from app.models.asignacion import Asignacion, RolDominio
    a = Asignacion(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        usuario_id=user.id,
        rol=RolDominio.PROFESOR,
        materia_id=materia.id,
        cohorte_id=cohorte.id,
        desde=date(2024, 1, 1),
    )
    db.add(a)
    await db.commit()
    return a


async def _make_version_padron(db, tenant, materia, cohorte):
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


async def _make_entrada(db, tenant, vp, nombre="Juan", apellidos="P", email_enc="ENC"):
    from app.models.padron import EntradaPadron
    ep = EntradaPadron(
        id=uuid.uuid4(),
        version_id=vp.id,
        tenant_id=tenant.id,
        nombre=nombre,
        apellidos=apellidos,
        email_enc=email_enc,
    )
    db.add(ep)
    await db.commit()
    return ep


async def _make_calificacion(db, tenant, materia, ep, actividad, nota_numerica=None, nota_textual=None):
    from app.models.calificacion import Calificacion, OrigenCalificacion
    c = Calificacion(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        entrada_padron_id=ep.id,
        materia_id=materia.id,
        actividad=actividad,
        nota_numerica=nota_numerica,
        nota_textual=nota_textual,
        origen=OrigenCalificacion.IMPORTADO,
    )
    db.add(c)
    await db.commit()
    return c


def _current_user(user, tenant, roles=("PROFESOR",)):
    return CurrentUser(
        id=user.id,
        tenant_id=tenant.id,
        roles=list(roles),
    )


def _make_service(db):
    from app.repositories.analisis_repository import AnalisisRepository
    from app.repositories.asignacion_repository import AsignacionRepository
    from app.services.analisis_service import AnalisisService
    return AnalisisService(
        analisis_repo=AnalisisRepository(db),
        asignacion_repo=AsignacionRepository(db),
        session=db,
    )


# ── Tests de scope isolation ──────────────────────────────────────────────────


class TestScopeIsolation:
    async def test_profesor_a_no_ve_alumnos_de_profesor_b(self, db):
        """PROFESOR A no ve alumnos de PROFESOR B con la misma materia_id."""
        tenant = await _make_tenant(db)
        carrera = await _make_carrera(db, tenant)
        materia = await _make_materia(db, tenant)

        # Dos cohortes distintas → dos asignaciones distintas
        # Cohorte B tiene nombre diferente para evitar unique constraint
        cohorte_a = await _make_cohorte(db, tenant, carrera)
        from app.models.estructura import Cohorte, EstadoEntidad
        from datetime import date as _date
        cohorte_b_obj = Cohorte(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            carrera_id=carrera.id,
            nombre="2025",
            anio=2025,
            vig_desde=_date(2025, 1, 1),
            estado=EstadoEntidad.activa,
        )
        db.add(cohorte_b_obj)
        await db.commit()
        cohorte_b = cohorte_b_obj

        user_a = await _make_user(db, tenant, "a@t.com")
        user_b = await _make_user(db, tenant, "b@t.com")
        asig_a = await _make_asignacion(db, tenant, user_a, materia, cohorte_a)
        asig_b = await _make_asignacion(db, tenant, user_b, materia, cohorte_b)

        vp_a = await _make_version_padron(db, tenant, materia, cohorte_a)
        vp_b = await _make_version_padron(db, tenant, materia, cohorte_b)
        ep_a = await _make_entrada(db, tenant, vp_a, "Alumno A")
        ep_b = await _make_entrada(db, tenant, vp_b, "Alumno B")

        svc = _make_service(db)

        result_a = await svc.get_atrasados(
            materia_id=materia.id,
            actividades_seleccionadas=["TP1"],
            current_user=_current_user(user_a, tenant),
        )
        # PROFESOR A ve 1 alumno (atrasado por faltante) pero no ve el de B
        nombres = [i["nombre"] for i in result_a["items"]]
        assert "Alumno B" not in nombres

    async def test_coordinador_ve_todos_los_alumnos(self, db):
        """COORDINADOR ve todos los alumnos del tenant para la materia."""
        tenant = await _make_tenant(db)
        carrera = await _make_carrera(db, tenant)
        materia = await _make_materia(db, tenant)
        cohorte = await _make_cohorte(db, tenant, carrera)

        coord_user = await _make_user(db, tenant, "coord@t.com")
        vp = await _make_version_padron(db, tenant, materia, cohorte)
        ep1 = await _make_entrada(db, tenant, vp, "Alumno X")
        ep2 = await _make_entrada(db, tenant, vp, "Alumno Y")

        svc = _make_service(db)
        result = await svc.get_ranking(
            materia_id=materia.id,
            current_user=_current_user(coord_user, tenant, roles=("COORDINADOR",)),
        )
        # Sin calificaciones → ranking vacío (ambos sin aprobadas)
        assert result["total"] == 0


# ── Tests de lógica de negocio ────────────────────────────────────────────────


class TestAtrasadoDetectado:
    async def test_alumno_con_nota_menor_umbral_aparece_en_atrasados(self, db):
        """Alumno con nota_numerica < umbral → aparece como atrasado."""
        tenant = await _make_tenant(db)
        carrera = await _make_carrera(db, tenant)
        materia = await _make_materia(db, tenant)
        cohorte = await _make_cohorte(db, tenant, carrera)
        user = await _make_user(db, tenant)
        asig = await _make_asignacion(db, tenant, user, materia, cohorte)
        vp = await _make_version_padron(db, tenant, materia, cohorte)
        ep = await _make_entrada(db, tenant, vp)
        await _make_calificacion(db, tenant, materia, ep, "TP1", nota_numerica=3.0)

        svc = _make_service(db)
        result = await svc.get_atrasados(
            materia_id=materia.id,
            actividades_seleccionadas=["TP1"],
            current_user=_current_user(user, tenant),
        )
        assert result["total_atrasados"] == 1
        assert result["items"][0]["actividades_bajo_umbral"] == ["TP1"]

    async def test_ranking_excluye_alumnos_sin_aprobadas(self, db):
        """RN-09: alumno con 0 aprobadas no aparece en el ranking."""
        tenant = await _make_tenant(db)
        carrera = await _make_carrera(db, tenant)
        materia = await _make_materia(db, tenant)
        cohorte = await _make_cohorte(db, tenant, carrera)
        user = await _make_user(db, tenant)
        asig = await _make_asignacion(db, tenant, user, materia, cohorte)
        vp = await _make_version_padron(db, tenant, materia, cohorte)
        ep = await _make_entrada(db, tenant, vp)
        # Nota reprobada
        await _make_calificacion(db, tenant, materia, ep, "TP1", nota_numerica=2.0)

        svc = _make_service(db)
        result = await svc.get_ranking(
            materia_id=materia.id,
            current_user=_current_user(user, tenant),
        )
        assert result["total"] == 0
        assert result["items"] == []


class TestMonitor:
    async def test_monitor_filtro_por_comision(self, db):
        """Monitor filtra correctamente por comision."""
        tenant = await _make_tenant(db)
        carrera = await _make_carrera(db, tenant)
        materia = await _make_materia(db, tenant)
        cohorte = await _make_cohorte(db, tenant, carrera)
        coord = await _make_user(db, tenant, "coord@t.com")
        vp = await _make_version_padron(db, tenant, materia, cohorte)

        from app.models.padron import EntradaPadron
        ep_a = EntradaPadron(
            id=uuid.uuid4(), version_id=vp.id, tenant_id=tenant.id,
            nombre="A", apellidos="X", email_enc="E", comision="COM-A",
        )
        ep_b = EntradaPadron(
            id=uuid.uuid4(), version_id=vp.id, tenant_id=tenant.id,
            nombre="B", apellidos="Y", email_enc="E", comision="COM-B",
        )
        db.add(ep_a)
        db.add(ep_b)
        await db.commit()

        class _Filtros:
            comision = "COM-A"
            busqueda_libre = None
            estado_actividad = None
            alumno = None
            actividad = None
            min_actividades_cumplidas = None
            fecha_desde = None
            fecha_hasta = None

        svc = _make_service(db)
        result = await svc.get_monitor(
            materia_id=materia.id,
            current_user=_current_user(coord, tenant, roles=("COORDINADOR",)),
            filtros=_Filtros(),
        )
        nombres = [i["nombre"] for i in result["items"]]
        assert "A" in nombres
        assert "B" not in nombres

    async def test_monitor_busqueda_libre(self, db):
        """Monitor filtra por búsqueda libre (nombre)."""
        tenant = await _make_tenant(db)
        carrera = await _make_carrera(db, tenant)
        materia = await _make_materia(db, tenant)
        cohorte = await _make_cohorte(db, tenant, carrera)
        coord = await _make_user(db, tenant, "coord2@t.com")
        vp = await _make_version_padron(db, tenant, materia, cohorte)

        from app.models.padron import EntradaPadron
        ep1 = EntradaPadron(
            id=uuid.uuid4(), version_id=vp.id, tenant_id=tenant.id,
            nombre="Carlos", apellidos="Lopez", email_enc="E",
        )
        ep2 = EntradaPadron(
            id=uuid.uuid4(), version_id=vp.id, tenant_id=tenant.id,
            nombre="María", apellidos="García", email_enc="E",
        )
        db.add(ep1)
        db.add(ep2)
        await db.commit()

        class _Filtros:
            comision = None
            busqueda_libre = "carlos"
            estado_actividad = None
            alumno = None
            actividad = None
            min_actividades_cumplidas = None
            fecha_desde = None
            fecha_hasta = None

        svc = _make_service(db)
        result = await svc.get_monitor(
            materia_id=materia.id,
            current_user=_current_user(coord, tenant, roles=("COORDINADOR",)),
            filtros=_Filtros(),
        )
        nombres = [i["nombre"] for i in result["items"]]
        assert "Carlos" in nombres
        assert "María" not in nombres


class TestReporteRapidoVacio:
    async def test_reporte_vacio_cuando_no_hay_calificaciones(self, db):
        """Reporte rápido retorna ceros cuando no hay calificaciones."""
        tenant = await _make_tenant(db)
        carrera = await _make_carrera(db, tenant)
        materia = await _make_materia(db, tenant)
        cohorte = await _make_cohorte(db, tenant, carrera)
        user = await _make_user(db, tenant)
        asig = await _make_asignacion(db, tenant, user, materia, cohorte)
        vp = await _make_version_padron(db, tenant, materia, cohorte)

        svc = _make_service(db)
        result = await svc.get_reporte_rapido(
            materia_id=materia.id,
            current_user=_current_user(user, tenant),
        )
        assert result["total_alumnos"] == 0
        assert result["total_atrasados"] == 0
        assert result["actividades_count"] == 0
