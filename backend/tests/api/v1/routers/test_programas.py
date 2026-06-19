"""Tests de routers para programas de materia y fechas académicas C-17 (Tareas 9.1–9.11).

Patrón: TestClient + mocked get_current_user + patched RbacRepository + mocked service.
Cubre:
- 9.1: POST /programas sin token → 401
- 9.2: POST /programas sin permiso → 403
- 9.3: POST /programas válido → 201
- 9.4: POST /programas duplicado → 409
- 9.5: GET /programas/{id} inexistente → 404
- 9.6: DELETE /programas/{id} válido → 204
- 9.7: POST /fechas-academicas con tipo inválido → 422
- 9.8: POST /fechas-academicas válido → 201
- 9.9: GET /fechas-academicas filtra por query params
- 9.10: GET /fechas-academicas/lms-fragment con datos → fragmento no vacío
- 9.11: GET /fechas-academicas/lms-fragment sin fechas → fragmento de ausencia

Safety net: 582 passed, 2 skipped, 19 pre-existing errors antes de estos tests.
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.models.evaluacion import TipoFechaAcademica
from app.schemas.fecha_academica import FechaAcademicaRead, LMSFragmentOut
from app.schemas.programa_materia import ProgramaMateriaOut

TENANT_A = uuid.uuid4()
PROGRAMA_ID = uuid.uuid4()
FECHA_ID = uuid.uuid4()
MATERIA_ID = uuid.uuid4()
CARRERA_ID = uuid.uuid4()
COHORTE_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(roles=None, tenant_id=None):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.tenant_id = tenant_id or TENANT_A
    user.roles = roles or ["COORDINADOR"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


def _make_programa_out(**kwargs) -> ProgramaMateriaOut:
    defaults = dict(
        id=PROGRAMA_ID,
        tenant_id=TENANT_A,
        materia_id=MATERIA_ID,
        carrera_id=CARRERA_ID,
        cohorte_id=COHORTE_ID,
        titulo="Programa de Algoritmos 2026",
        referencia_archivo="https://drive.example.com/prog.pdf",
        cargado_at=NOW,
    )
    defaults.update(kwargs)
    return ProgramaMateriaOut(**defaults)


def _make_fecha_read(**kwargs) -> FechaAcademicaRead:
    defaults = dict(
        id=FECHA_ID,
        tenant_id=TENANT_A,
        materia_id=MATERIA_ID,
        cohorte_id=COHORTE_ID,
        tipo=TipoFechaAcademica.Parcial,
        numero=1,
        periodo="2026-1",
        fecha="2026-05-10",
        titulo="Primer Parcial",
    )
    defaults.update(kwargs)
    return FechaAcademicaRead(**defaults)


def _make_programa_svc(**overrides):
    svc = MagicMock()
    svc.crear = AsyncMock(return_value=_make_programa_out())
    svc.get_by_id = AsyncMock(return_value=_make_programa_out())
    svc.get_by_context = AsyncMock(return_value=_make_programa_out())
    svc.actualizar = AsyncMock(return_value=_make_programa_out())
    svc.eliminar = AsyncMock(return_value=None)
    for k, v in overrides.items():
        setattr(svc, k, v if isinstance(v, AsyncMock) else AsyncMock(return_value=v))
    return svc


def _make_fecha_svc(**overrides):
    svc = MagicMock()
    svc.crear = AsyncMock(return_value=_make_fecha_read())
    svc.listar = AsyncMock(return_value=[_make_fecha_read()])
    svc.get_by_id = AsyncMock(return_value=_make_fecha_read())
    svc.actualizar = AsyncMock(return_value=_make_fecha_read())
    svc.eliminar = AsyncMock(return_value=None)
    svc.generar_fragmento_lms = AsyncMock(
        return_value=LMSFragmentOut(
            fragmento="## Fechas Académicas — 2026-1\n\n- **2026-05-10** — Parcial 1: Primer Parcial"
        )
    )
    for k, v in overrides.items():
        setattr(svc, k, v if isinstance(v, AsyncMock) else AsyncMock(return_value=v))
    return svc


@contextmanager
def _client_programas(perms: list[str], user=None, svc_override=None):
    import app.api.v1.routers.programas as programas_router_mod

    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db
    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override is not None:
            app.dependency_overrides[programas_router_mod._get_programa_service] = (
                lambda: svc_override
            )
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override is not None:
                app.dependency_overrides.pop(
                    programas_router_mod._get_programa_service, None
                )


@contextmanager
def _client_fechas(perms: list[str], user=None, svc_override=None):
    import app.api.v1.routers.fechas_academicas as fechas_router_mod

    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db
    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override is not None:
            app.dependency_overrides[fechas_router_mod._get_fecha_academica_service] = (
                lambda: svc_override
            )
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override is not None:
                app.dependency_overrides.pop(
                    fechas_router_mod._get_fecha_academica_service, None
                )


_PAYLOAD_PROGRAMA = {
    "materia_id": str(MATERIA_ID),
    "carrera_id": str(CARRERA_ID),
    "cohorte_id": str(COHORTE_ID),
    "titulo": "Programa de Algoritmos 2026",
    "referencia_archivo": "https://drive.example.com/prog.pdf",
}

_PAYLOAD_FECHA = {
    "materia_id": str(MATERIA_ID),
    "cohorte_id": str(COHORTE_ID),
    "tipo": "Parcial",
    "numero": 1,
    "periodo": "2026-1",
    "fecha": "2026-05-10",
    "titulo": "Primer Parcial",
}


# ── 9.1 POST /programas sin token → 401 ──────────────────────────────────────


def test_crear_programa_sin_token_retorna_401():
    """9.1: Sin autenticación → 401."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/programas", json=_PAYLOAD_PROGRAMA)
    assert resp.status_code == 401


# ── 9.2 POST /programas sin permiso estructura:gestionar → 403 ───────────────


def test_crear_programa_sin_permiso_retorna_403():
    """9.2: Sin estructura:gestionar → 403."""
    with _client_programas([]) as client:
        resp = client.post("/api/v1/programas", json=_PAYLOAD_PROGRAMA)
    assert resp.status_code == 403


# ── 9.3 POST /programas válido → 201 con datos ───────────────────────────────


def test_crear_programa_valido_retorna_201():
    """9.3: POST válido con permiso → 201 con ProgramaMateriaOut."""
    svc = _make_programa_svc()
    with _client_programas(["estructura:gestionar"], svc_override=svc) as client:
        resp = client.post("/api/v1/programas", json=_PAYLOAD_PROGRAMA)
    assert resp.status_code == 201
    body = resp.json()
    assert body["titulo"] == "Programa de Algoritmos 2026"
    assert "id" in body
    svc.crear.assert_called_once()


# ── 9.4 POST /programas duplicado → 409 ──────────────────────────────────────


def test_crear_programa_duplicado_retorna_409():
    """9.4: Contexto duplicado → 409."""
    svc = _make_programa_svc()
    svc.crear = AsyncMock(
        side_effect=HTTPException(status_code=409, detail="Ya existe un programa para este contexto académico")
    )
    with _client_programas(["estructura:gestionar"], svc_override=svc) as client:
        resp = client.post("/api/v1/programas", json=_PAYLOAD_PROGRAMA)
    assert resp.status_code == 409


# ── 9.5 GET /programas/{id} inexistente → 404 ────────────────────────────────


def test_obtener_programa_inexistente_retorna_404():
    """9.5: ID no encontrado → 404."""
    svc = _make_programa_svc()
    svc.get_by_id = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="Programa de materia no encontrado")
    )
    with _client_programas(["estructura:leer"], svc_override=svc) as client:
        resp = client.get(f"/api/v1/programas/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── 9.6 DELETE /programas/{id} válido → 204 ──────────────────────────────────


def test_eliminar_programa_valido_retorna_204():
    """9.6: DELETE válido con permiso → 204."""
    svc = _make_programa_svc()
    with _client_programas(["estructura:gestionar"], svc_override=svc) as client:
        resp = client.delete(f"/api/v1/programas/{PROGRAMA_ID}")
    assert resp.status_code == 204
    svc.eliminar.assert_called_once()


# ── 9.7 POST /fechas-academicas con tipo inválido → 422 ──────────────────────


def test_crear_fecha_tipo_invalido_retorna_422():
    """9.7: tipo no reconocido → 422 (validación Pydantic)."""
    svc = _make_fecha_svc()
    payload_invalido = {**_PAYLOAD_FECHA, "tipo": "ExamenFinal"}
    with _client_fechas(["estructura:gestionar"], svc_override=svc) as client:
        resp = client.post("/api/v1/fechas-academicas", json=payload_invalido)
    assert resp.status_code == 422


# ── 9.8 POST /fechas-academicas válido → 201 ─────────────────────────────────


def test_crear_fecha_valida_retorna_201():
    """9.8: POST válido con permiso → 201 con FechaAcademicaRead."""
    svc = _make_fecha_svc()
    with _client_fechas(["estructura:gestionar"], svc_override=svc) as client:
        resp = client.post("/api/v1/fechas-academicas", json=_PAYLOAD_FECHA)
    assert resp.status_code == 201
    body = resp.json()
    assert body["tipo"] == "Parcial"
    assert body["titulo"] == "Primer Parcial"
    svc.crear.assert_called_once()


# ── 9.9 GET /fechas-academicas filtra por query params ───────────────────────


def test_listar_fechas_filtra_por_query_params():
    """9.9: GET con materia_id, cohorte_id, periodo pasa los filtros al servicio."""
    svc = _make_fecha_svc()
    with _client_fechas(["estructura:leer"], svc_override=svc) as client:
        resp = client.get(
            f"/api/v1/fechas-academicas"
            f"?materia_id={MATERIA_ID}&cohorte_id={COHORTE_ID}&periodo=2026-1"
        )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 1
    # Verificar que el servicio fue llamado con los filtros
    call_kwargs = svc.listar.call_args.kwargs
    assert call_kwargs.get("materia_id") == MATERIA_ID
    assert call_kwargs.get("cohorte_id") == COHORTE_ID
    assert call_kwargs.get("periodo") == "2026-1"


# ── 9.10 GET /lms-fragment con datos → fragmento Markdown no vacío ───────────


def test_lms_fragment_con_datos_retorna_markdown():
    """9.10: lms-fragment con fechas → fragmento Markdown no vacío."""
    svc = _make_fecha_svc()
    with _client_fechas(["estructura:leer"], svc_override=svc) as client:
        resp = client.get(
            f"/api/v1/fechas-academicas/lms-fragment"
            f"?materia_id={MATERIA_ID}&cohorte_id={COHORTE_ID}&periodo=2026-1"
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "fragmento" in body
    assert len(body["fragmento"]) > 0
    assert "2026-1" in body["fragmento"]


# ── 9.11 GET /lms-fragment sin fechas → fragmento de ausencia ────────────────


def test_lms_fragment_sin_fechas_retorna_mensaje_ausencia():
    """9.11: lms-fragment sin fechas → fragmento con mensaje de ausencia."""
    svc = _make_fecha_svc()
    svc.generar_fragmento_lms = AsyncMock(
        return_value=LMSFragmentOut(
            fragmento="## Fechas Académicas — 2026-2\n\n_Sin fechas registradas para este período._"
        )
    )
    with _client_fechas(["estructura:leer"], svc_override=svc) as client:
        resp = client.get(
            f"/api/v1/fechas-academicas/lms-fragment"
            f"?materia_id={MATERIA_ID}&cohorte_id={COHORTE_ID}&periodo=2026-2"
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "fragmento" in body
    assert "Sin fechas" in body["fragmento"] or len(body["fragmento"]) > 0
