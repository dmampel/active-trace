"""Tests unitarios para los schemas de equipo (validaciones Pydantic).

No requieren DB — validan solo la lógica de los modelos Pydantic.
"""
import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.equipo import (
    AsignacionMasivaRequest,
    BuscarUsuariosQuery,
    ClonarEquipoRequest,
    ContextoEquipo,
    VigenciaEquipoRequest,
)


# ── VigenciaEquipoRequest: al menos desde o hasta ────────────────────────────

def test_vigencia_sin_fechas_raises():
    """VigenciaEquipoRequest sin desde ni hasta → ValidationError."""
    with pytest.raises(ValidationError):
        VigenciaEquipoRequest(cohorte_id=uuid.uuid4())


def test_vigencia_solo_hasta_ok():
    """VigenciaEquipoRequest con solo hasta → válido."""
    req = VigenciaEquipoRequest(cohorte_id=uuid.uuid4(), hasta=date(2025, 12, 31))
    assert req.hasta == date(2025, 12, 31)
    assert req.desde is None


def test_vigencia_solo_desde_ok():
    """VigenciaEquipoRequest con solo desde → válido."""
    req = VigenciaEquipoRequest(cohorte_id=uuid.uuid4(), desde=date.today())
    assert req.desde == date.today()
    assert req.hasta is None


def test_vigencia_ambas_fechas_ok():
    """VigenciaEquipoRequest con desde y hasta → válido."""
    req = VigenciaEquipoRequest(
        cohorte_id=uuid.uuid4(),
        desde=date(2024, 3, 1),
        hasta=date(2024, 12, 31),
    )
    assert req.desde is not None
    assert req.hasta is not None


# ── AsignacionMasivaRequest: usuario_ids min 1 ───────────────────────────────

def test_masiva_usuario_ids_vacio_raises():
    """AsignacionMasivaRequest con usuario_ids=[] → ValidationError."""
    with pytest.raises(ValidationError):
        AsignacionMasivaRequest(
            usuario_ids=[],
            cohorte_id=uuid.uuid4(),
            rol="PROFESOR",
            desde=date.today(),
        )


def test_masiva_usuario_ids_un_elemento_ok():
    """AsignacionMasivaRequest con un usuario_id → válido."""
    req = AsignacionMasivaRequest(
        usuario_ids=[uuid.uuid4()],
        cohorte_id=uuid.uuid4(),
        rol="PROFESOR",
        desde=date.today(),
    )
    assert len(req.usuario_ids) == 1


# ── BuscarUsuariosQuery: q min_length=2 ──────────────────────────────────────

def test_buscar_q_too_short_raises():
    """BuscarUsuariosQuery con q de 1 char → ValidationError."""
    with pytest.raises(ValidationError):
        BuscarUsuariosQuery(q="a")


def test_buscar_q_dos_chars_ok():
    """BuscarUsuariosQuery con q de 2 chars → válido."""
    req = BuscarUsuariosQuery(q="ga")
    assert req.q == "ga"
    assert req.limit == 20  # default


def test_buscar_limit_max_50():
    """BuscarUsuariosQuery con limit=51 → ValidationError."""
    with pytest.raises(ValidationError):
        BuscarUsuariosQuery(q="garcia", limit=51)


def test_buscar_limit_50_ok():
    """BuscarUsuariosQuery con limit=50 → válido."""
    req = BuscarUsuariosQuery(q="garcia", limit=50)
    assert req.limit == 50


# ── extra='forbid' en todos los schemas ──────────────────────────────────────

def test_vigencia_campo_extra_raises():
    """Campo extra en VigenciaEquipoRequest → ValidationError (extra=forbid)."""
    with pytest.raises(ValidationError):
        VigenciaEquipoRequest(
            cohorte_id=uuid.uuid4(),
            hasta=date(2025, 12, 31),
            campo_inesperado="x",
        )


def test_clonar_campo_extra_raises():
    """Campo extra en ClonarEquipoRequest → ValidationError (extra=forbid)."""
    with pytest.raises(ValidationError):
        ClonarEquipoRequest(
            origen=ContextoEquipo(cohorte_id=uuid.uuid4()),
            destino=ContextoEquipo(cohorte_id=uuid.uuid4()),
            campo_inesperado="x",
        )
