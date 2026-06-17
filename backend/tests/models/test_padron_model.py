"""Tests para los modelos VersionPadron, EntradaPadron y TenantMoodleConfig.

TDD: estas pruebas validan que los modelos existen, tienen los campos requeridos,
los mixins correctos y las constraints esperadas.
Usan SQLite en memoria (sin PG) para ser rápidos y sin dependencias de infraestructura.
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
    from app.models.padron import EntradaPadron, VersionPadron
    from app.models.tenant_moodle_config import TenantMoodleConfig  # noqa: F401

    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
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


# ── VersionPadron ─────────────────────────────────────────────────────────────


def test_version_padron_inherits_mixins():
    from app.models.padron import VersionPadron

    assert issubclass(VersionPadron, UUIDMixin)
    assert issubclass(VersionPadron, TimestampMixin)
    assert issubclass(VersionPadron, SoftDeleteMixin)
    assert issubclass(VersionPadron, TenantMixin)


def test_version_padron_has_required_columns():
    from app.models.padron import VersionPadron

    insp = inspect(VersionPadron)
    column_names = {c.key for c in insp.mapper.column_attrs}

    assert "materia_id" in column_names
    assert "cohorte_id" in column_names
    assert "cargado_por" in column_names
    assert "cargado_at" in column_names
    assert "activa" in column_names


def test_version_padron_can_be_created(session, tenant):
    from app.models.padron import VersionPadron

    materia_id = uuid.uuid4()
    cohorte_id = uuid.uuid4()
    user_id = uuid.uuid4()

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        cargado_por=user_id,
        activa=True,
    )
    session.add(vp)
    session.commit()
    session.refresh(vp)

    assert vp.id is not None
    assert vp.activa is True
    assert vp.deleted_at is None


def test_version_padron_activa_defaults_true(session, tenant):
    from app.models.padron import VersionPadron

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        cargado_por=uuid.uuid4(),
    )
    session.add(vp)
    session.commit()
    session.refresh(vp)

    assert vp.activa is True


# ── EntradaPadron ─────────────────────────────────────────────────────────────


def test_entrada_padron_has_required_columns():
    from app.models.padron import EntradaPadron

    insp = inspect(EntradaPadron)
    column_names = {c.key for c in insp.mapper.column_attrs}

    assert "version_id" in column_names
    assert "tenant_id" in column_names
    assert "nombre" in column_names
    assert "apellidos" in column_names
    assert "email_enc" in column_names
    assert "comision" in column_names
    assert "regional" in column_names
    assert "usuario_id" in column_names


def test_entrada_padron_can_be_created(session, tenant):
    from app.models.padron import EntradaPadron, VersionPadron

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        cargado_por=uuid.uuid4(),
        activa=True,
    )
    session.add(vp)
    session.commit()

    entrada = EntradaPadron(
        version_id=vp.id,
        tenant_id=tenant.id,
        nombre="Juan",
        apellidos="Pérez",
        email_enc="CIFRADO_TEST",
        comision="A",
    )
    session.add(entrada)
    session.commit()
    session.refresh(entrada)

    assert entrada.id is not None
    assert entrada.email_enc == "CIFRADO_TEST"
    assert entrada.usuario_id is None


# ── TenantMoodleConfig ────────────────────────────────────────────────────────


def test_tenant_moodle_config_inherits_mixins():
    from app.models.tenant_moodle_config import TenantMoodleConfig

    assert issubclass(TenantMoodleConfig, UUIDMixin)
    assert issubclass(TenantMoodleConfig, TimestampMixin)


def test_tenant_moodle_config_has_required_columns():
    from app.models.tenant_moodle_config import TenantMoodleConfig

    insp = inspect(TenantMoodleConfig)
    column_names = {c.key for c in insp.mapper.column_attrs}

    assert "tenant_id" in column_names
    assert "moodle_url_enc" in column_names
    assert "moodle_token_enc" in column_names


def test_tenant_moodle_config_can_be_created(session, tenant):
    from app.models.tenant_moodle_config import TenantMoodleConfig

    config = TenantMoodleConfig(
        tenant_id=tenant.id,
        moodle_url_enc="URL_CIFRADA",
        moodle_token_enc="TOKEN_CIFRADO",
    )
    session.add(config)
    session.commit()
    session.refresh(config)

    assert config.id is not None
    assert config.moodle_url_enc == "URL_CIFRADA"
