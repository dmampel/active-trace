"""Tests para los modelos Calificacion y UmbralMateria (C-10).

TDD RED fase: valida que los modelos tienen los campos requeridos, los mixins correctos
y las constraints esperadas. Usa SQLite en memoria para tests de estructura (sin PG).
"""

import uuid

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin
from app.models.tenant import Tenant


@pytest.fixture(scope="module")
def engine():
    # Importar todos los modelos para registrar en metadata
    import app.models  # noqa: F401
    from app.models.calificacion import Calificacion, UmbralMateria  # noqa: F401

    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng, checkfirst=True)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def tenant(session):
    t = Tenant(name=f"Tenant-{uuid.uuid4().hex[:8]}")
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


# ── Calificacion ──────────────────────────────────────────────────────────────


def test_calificacion_inherits_mixins():
    from app.models.calificacion import Calificacion

    assert issubclass(Calificacion, UUIDMixin)
    assert issubclass(Calificacion, TimestampMixin)
    assert issubclass(Calificacion, SoftDeleteMixin)
    assert issubclass(Calificacion, TenantMixin)


def test_calificacion_has_required_columns():
    from app.models.calificacion import Calificacion

    insp = inspect(Calificacion)
    column_names = {c.key for c in insp.mapper.column_attrs}

    assert "entrada_padron_id" in column_names
    assert "materia_id" in column_names
    assert "actividad" in column_names
    assert "nota_numerica" in column_names
    assert "nota_textual" in column_names
    assert "origen" in column_names
    assert "importado_at" in column_names
    assert "tenant_id" in column_names
    # aprobado NO debe existir como columna (D2 — se deriva en función pura)
    assert "aprobado" not in column_names


def test_calificacion_can_be_created(session, tenant):
    from app.models.calificacion import Calificacion, OrigenCalificacion
    from app.models.padron import EntradaPadron, VersionPadron
    from datetime import datetime, timezone

    # Crear padrón mínimo para FK
    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        cargado_por=uuid.uuid4(),
        activa=True,
    )
    session.add(vp)
    session.flush()

    entrada = EntradaPadron(
        version_id=vp.id,
        tenant_id=tenant.id,
        nombre="Ana",
        apellidos="García",
        email_enc="CIFRADO",
    )
    session.add(entrada)
    session.flush()

    cal = Calificacion(
        entrada_padron_id=entrada.id,
        materia_id=uuid.uuid4(),
        actividad="TP1",
        nota_numerica=8.5,
        nota_textual=None,
        origen=OrigenCalificacion.IMPORTADO,
        importado_at=datetime.now(timezone.utc),
        tenant_id=tenant.id,
    )
    session.add(cal)
    session.commit()
    session.refresh(cal)

    assert cal.id is not None
    assert cal.nota_numerica == 8.5
    assert cal.nota_textual is None
    assert cal.deleted_at is None


def test_calificacion_nota_textual(session, tenant):
    """Calificación con solo nota textual, sin nota numérica."""
    from app.models.calificacion import Calificacion, OrigenCalificacion
    from app.models.padron import EntradaPadron, VersionPadron
    from datetime import datetime, timezone

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        cargado_por=uuid.uuid4(),
        activa=True,
    )
    session.add(vp)
    session.flush()

    entrada = EntradaPadron(
        version_id=vp.id,
        tenant_id=tenant.id,
        nombre="Pedro",
        apellidos="López",
        email_enc="CIFRADO2",
    )
    session.add(entrada)
    session.flush()

    cal = Calificacion(
        entrada_padron_id=entrada.id,
        materia_id=uuid.uuid4(),
        actividad="Entrega Final",
        nota_numerica=None,
        nota_textual="Satisfactorio",
        origen=OrigenCalificacion.IMPORTADO,
        importado_at=datetime.now(timezone.utc),
        tenant_id=tenant.id,
    )
    session.add(cal)
    session.commit()
    session.refresh(cal)

    assert cal.nota_numerica is None
    assert cal.nota_textual == "Satisfactorio"


def test_calificacion_soft_delete(session, tenant):
    """Soft delete no borra físicamente la fila."""
    from app.models.calificacion import Calificacion, OrigenCalificacion
    from app.models.padron import EntradaPadron, VersionPadron
    from datetime import datetime, timezone

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        cargado_por=uuid.uuid4(),
        activa=True,
    )
    session.add(vp)
    session.flush()

    entrada = EntradaPadron(
        version_id=vp.id,
        tenant_id=tenant.id,
        nombre="Luis",
        apellidos="Martínez",
        email_enc="CIFRADO3",
    )
    session.add(entrada)
    session.flush()

    cal = Calificacion(
        entrada_padron_id=entrada.id,
        materia_id=uuid.uuid4(),
        actividad="Coloquio",
        nota_numerica=6.0,
        origen=OrigenCalificacion.IMPORTADO,
        importado_at=datetime.now(timezone.utc),
        tenant_id=tenant.id,
    )
    session.add(cal)
    session.commit()
    session.refresh(cal)

    # Soft delete
    cal.deleted_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(cal)

    assert cal.deleted_at is not None
    assert cal.id is not None  # fila sigue existiendo


# ── UmbralMateria ─────────────────────────────────────────────────────────────


def test_umbral_materia_inherits_mixins():
    from app.models.calificacion import UmbralMateria

    assert issubclass(UmbralMateria, UUIDMixin)
    assert issubclass(UmbralMateria, TimestampMixin)
    assert issubclass(UmbralMateria, SoftDeleteMixin)
    assert issubclass(UmbralMateria, TenantMixin)


def test_umbral_materia_has_required_columns():
    from app.models.calificacion import UmbralMateria

    insp = inspect(UmbralMateria)
    column_names = {c.key for c in insp.mapper.column_attrs}

    assert "asignacion_id" in column_names
    assert "materia_id" in column_names
    assert "umbral_pct" in column_names
    assert "valores_aprobatorios" in column_names
    assert "tenant_id" in column_names


def test_umbral_materia_can_be_created(session, tenant):
    from app.models.calificacion import UmbralMateria

    um = UmbralMateria(
        asignacion_id=uuid.uuid4(),
        materia_id=uuid.uuid4(),
        umbral_pct=70,
        valores_aprobatorios=["Satisfactorio", "Supera lo esperado"],
        tenant_id=tenant.id,
    )
    session.add(um)
    session.commit()
    session.refresh(um)

    assert um.id is not None
    assert um.umbral_pct == 70
    assert "Satisfactorio" in um.valores_aprobatorios


def test_umbral_materia_default_umbral_pct(session, tenant):
    """El umbral por defecto es 60%."""
    from app.models.calificacion import UmbralMateria

    um = UmbralMateria(
        asignacion_id=uuid.uuid4(),
        materia_id=uuid.uuid4(),
        valores_aprobatorios=[],
        tenant_id=tenant.id,
    )
    session.add(um)
    session.commit()
    session.refresh(um)

    assert um.umbral_pct == 60
