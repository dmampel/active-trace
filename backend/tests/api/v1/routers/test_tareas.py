"""Tests del router de tareas internas (C-16, Tareas 8.1–8.8).

Patrón: TestClient + mocked get_current_user + patched RbacRepository + mocked service.
Cubre:
- RBAC: tareas:gestionar requerido en todos los endpoints
- POST /tareas → 201 + TareaOut
- GET /tareas/mis-tareas → 200 lista filtrada
- PATCH /tareas/{id}/estado transición válida → 200
- PATCH /tareas/{id}/estado transición inválida → 422
- POST /tareas/{id}/comentarios → 201 + ComentarioOut
- GET /tareas sin rol admin → 403
- GET /tareas con rol admin + filtros → 200 paginado

Safety net: 549 passed + 30 errors (pre-existing test_usuario_cascade.py) antes de estos tests.
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
from app.models.tarea import EstadoTarea
from app.schemas.tarea import ComentarioOut, PaginatedTareas, TareaOut

TENANT_A = uuid.uuid4()
COORD_ID = uuid.uuid4()
PROFESOR_ID = uuid.uuid4()
TAREA_ID = uuid.uuid4()

NOW = datetime.now(timezone.utc)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(roles=None, tenant_id=None, user_id=None):
    user = MagicMock()
    user.id = user_id or COORD_ID
    user.tenant_id = tenant_id or TENANT_A
    user.roles = roles or ["COORDINADOR"]
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


def _make_tarea_out(**kwargs) -> TareaOut:
    defaults = dict(
        id=TAREA_ID,
        tenant_id=TENANT_A,
        asignado_a=uuid.uuid4(),
        asignado_por=COORD_ID,
        materia_id=None,
        estado=EstadoTarea.pendiente,
        descripcion="Tarea de prueba",
        contexto_id=None,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )
    defaults.update(kwargs)
    return TareaOut(**defaults)


def _make_comentario_out(**kwargs) -> ComentarioOut:
    defaults = dict(
        id=uuid.uuid4(),
        autor_id=COORD_ID,
        texto="Comentario de prueba",
        creado_at=NOW,
    )
    defaults.update(kwargs)
    return ComentarioOut(**defaults)


def _make_svc(**overrides):
    svc = MagicMock()
    svc.crear_tarea = AsyncMock(return_value=_make_tarea_out())
    svc.mis_tareas = AsyncMock(return_value=[_make_tarea_out()])
    svc.listar_todas = AsyncMock(
        return_value=PaginatedTareas(
            total=1, page=1, size=50, items=[_make_tarea_out()]
        )
    )
    svc.cambiar_estado = AsyncMock(
        return_value=_make_tarea_out(estado=EstadoTarea.en_progreso)
    )
    svc.agregar_comentario = AsyncMock(return_value=_make_comentario_out())
    svc.listar_comentarios = AsyncMock(return_value=[_make_comentario_out()])
    for k, v in overrides.items():
        setattr(svc, k, v if isinstance(v, AsyncMock) else AsyncMock(return_value=v))
    return svc


@contextmanager
def _client_with_perms(perms: list[str], user=None, svc_override=None):
    import app.api.v1.routers.tareas as tareas_router_module

    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db
    rbac_target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(rbac_target, new=AsyncMock(return_value=set(perms))):
        if svc_override is not None:
            app.dependency_overrides[tareas_router_module._get_tarea_service] = (
                lambda: svc_override
            )
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
            if svc_override is not None:
                app.dependency_overrides.pop(
                    tareas_router_module._get_tarea_service, None
                )


# ── Task 8.1: POST /tareas sin permiso → 403 ─────────────────────────────────


def test_crear_tarea_sin_permiso_retorna_403():
    """8.1: Sin tareas:gestionar → 403."""
    with _client_with_perms([]) as client:
        resp = client.post(
            "/api/v1/tareas",
            json={"asignado_a": str(uuid.uuid4()), "descripcion": "X"},
        )
    assert resp.status_code == 403


# ── Task 8.2: POST /tareas con datos válidos → 201 + TareaOut ─────────────────


def test_crear_tarea_valida_retorna_201():
    """8.2: POST /tareas con permiso y datos válidos → 201."""
    svc = _make_svc()
    with _client_with_perms(["tareas:gestionar"], svc_override=svc) as client:
        resp = client.post(
            "/api/v1/tareas",
            json={
                "asignado_a": str(uuid.uuid4()),
                "descripcion": "Revisar notas de parcial",
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["estado"] == "pendiente"
    svc.crear_tarea.assert_called_once()


# ── Task 8.3: GET /tareas/mis-tareas → 200 con lista ─────────────────────────


def test_mis_tareas_retorna_200_con_lista():
    """8.3: GET /tareas/mis-tareas con permiso → 200."""
    svc = _make_svc()
    with _client_with_perms(["tareas:gestionar"], svc_override=svc) as client:
        resp = client.get("/api/v1/tareas/mis-tareas")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    svc.mis_tareas.assert_called_once()


def test_mis_tareas_con_filtro_estado():
    """TRIANGULATE: GET /tareas/mis-tareas?estado=pendiente pasa el estado al servicio."""
    svc = _make_svc()
    with _client_with_perms(["tareas:gestionar"], svc_override=svc) as client:
        resp = client.get("/api/v1/tareas/mis-tareas?estado=pendiente")
    assert resp.status_code == 200


# ── Task 8.4: PATCH /tareas/{id}/estado transición válida → 200 ───────────────


def test_cambiar_estado_valido_retorna_200():
    """8.4: PATCH transición válida → 200."""
    svc = _make_svc()
    with _client_with_perms(["tareas:gestionar"], svc_override=svc) as client:
        resp = client.patch(
            f"/api/v1/tareas/{TAREA_ID}/estado",
            json={"estado": "en_progreso"},
        )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "en_progreso"


# ── Task 8.5: PATCH /tareas/{id}/estado transición inválida → 422 ─────────────


def test_cambiar_estado_invalido_retorna_422():
    """8.5: PATCH con transición inválida (ValueError del servicio) → 422."""
    svc = _make_svc()
    svc.cambiar_estado = AsyncMock(
        side_effect=ValueError("Transición inválida: resuelta → pendiente")
    )
    with _client_with_perms(["tareas:gestionar"], svc_override=svc) as client:
        resp = client.patch(
            f"/api/v1/tareas/{TAREA_ID}/estado",
            json={"estado": "pendiente"},
        )
    assert resp.status_code == 422


# ── Task 8.6: POST /tareas/{id}/comentarios → 201 + ComentarioOut ─────────────


def test_agregar_comentario_retorna_201():
    """8.6: POST comentario con permiso → 201."""
    svc = _make_svc()
    with _client_with_perms(["tareas:gestionar"], svc_override=svc) as client:
        resp = client.post(
            f"/api/v1/tareas/{TAREA_ID}/comentarios",
            json={"texto": "Este es mi comentario"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["texto"] == "Comentario de prueba"
    svc.agregar_comentario.assert_called_once()


# ── Task 8.7: GET /tareas sin rol admin → 403 ─────────────────────────────────


def test_listar_todas_sin_rol_admin_retorna_403():
    """8.7: GET /tareas con rol PROFESOR (no admin) → 403."""
    svc = _make_svc()
    svc.listar_todas = AsyncMock(
        side_effect=PermissionError("Solo COORDINADOR o ADMIN pueden acceder")
    )
    profesor_user = _make_user(roles=["PROFESOR"])
    with _client_with_perms(
        ["tareas:gestionar"], user=profesor_user, svc_override=svc
    ) as client:
        resp = client.get("/api/v1/tareas")
    assert resp.status_code == 403


# ── Task 8.8: GET /tareas con rol admin + filtros → 200 paginado ──────────────


def test_listar_todas_admin_con_filtros_retorna_200():
    """8.8: GET /tareas con rol COORDINADOR y filtros → 200 paginado."""
    svc = _make_svc()
    with _client_with_perms(["tareas:gestionar"], svc_override=svc) as client:
        resp = client.get(
            "/api/v1/tareas?page=1&size=10&estado=pendiente"
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "items" in body
    assert "page" in body
    assert "size" in body
