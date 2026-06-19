"""Tests unitarios para TareaService (C-16, Tareas 7.1–7.5).

Patrón: repos mockeados con AsyncMock — sin DB real.
Cubre: validación de tenant en crear_tarea, máquina de estados,
       autorización en cambiar_estado, restricción de rol en listar_todas.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.tarea import EstadoTarea
from app.schemas.tarea import TareaCreate
from app.services.tarea_service import TareaService, TRANSICIONES


# ── Helpers ───────────────────────────────────────────────────────────────────


_SENTINEL = object()  # sentinel para distinguir "no pasado" de None explícito


def _make_service(
    tarea_side_effect=None,
    tarea_get_by_id=_SENTINEL,
    usuario_get_by_id=_SENTINEL,
):
    tarea_repo = AsyncMock()
    comentario_repo = AsyncMock()
    usuario_repo = AsyncMock()

    if tarea_side_effect:
        tarea_repo.create.side_effect = tarea_side_effect
    if tarea_get_by_id is not _SENTINEL:
        tarea_repo.get_by_id.return_value = tarea_get_by_id
    if usuario_get_by_id is not _SENTINEL:
        usuario_repo.get_by_id.return_value = usuario_get_by_id

    return TareaService(tarea_repo, comentario_repo, usuario_repo)


def _make_tarea(
    estado=EstadoTarea.pendiente,
    asignado_a=None,
    asignado_por=None,
):
    """Devuelve un objeto con atributos reales (no mocks) para que model_validate funcione."""
    from datetime import datetime, timezone
    from types import SimpleNamespace

    t = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        estado=estado,
        asignado_a=asignado_a or uuid.uuid4(),
        asignado_por=asignado_por or uuid.uuid4(),
        materia_id=None,
        contexto_id=None,
        descripcion="desc",
        deleted_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return t


# ── Task 7.1: crear_tarea con asignado_a de otro tenant lanza error ───────────


async def test_crear_tarea_asignado_a_otro_tenant_lanza_error():
    """RED: crear_tarea debe lanzar 422 si asignado_a no pertenece al tenant."""
    from fastapi import HTTPException

    svc = _make_service(usuario_get_by_id=None)  # None = no existe en tenant

    data = TareaCreate(asignado_a=uuid.uuid4(), descripcion="Tarea")
    with pytest.raises(HTTPException) as exc_info:
        await svc.crear_tarea(uuid.uuid4(), uuid.uuid4(), data)

    assert exc_info.value.status_code == 422


async def test_crear_tarea_asignado_a_mismo_tenant_ok():
    """TRIANGULATE: crear_tarea con usuario válido del tenant no lanza error."""
    usuario_mock = MagicMock()
    svc = _make_service(usuario_get_by_id=usuario_mock)

    tarea_mock = _make_tarea()
    svc.repo.create.return_value = tarea_mock

    data = TareaCreate(asignado_a=uuid.uuid4(), descripcion="Tarea válida")
    result = await svc.crear_tarea(uuid.uuid4(), uuid.uuid4(), data)
    assert result is not None


# ── Task 7.2: _validar_transicion — todas las transiciones válidas pasan ──────


def test_validar_transicion_validas():
    """RED: todas las transiciones del dict TRANSICIONES deben pasar sin excepción."""
    svc = TareaService(AsyncMock(), AsyncMock(), AsyncMock())

    for estado_origen, destinos in TRANSICIONES.items():
        for destino in destinos:
            origen_enum = EstadoTarea(estado_origen)
            destino_enum = EstadoTarea(destino)
            # No debe lanzar
            svc._validar_transicion(origen_enum, destino_enum)


def test_validar_transicion_pendiente_a_en_progreso():
    """TRIANGULATE: caso concreto más común."""
    svc = TareaService(AsyncMock(), AsyncMock(), AsyncMock())
    # No debe lanzar
    svc._validar_transicion(EstadoTarea.pendiente, EstadoTarea.en_progreso)


# ── Task 7.3: _validar_transicion — estado terminal lanza ValueError ──────────


def test_validar_transicion_desde_resuelta_lanza_value_error():
    """RED: desde estado terminal 'resuelta' cualquier transición es inválida."""
    svc = TareaService(AsyncMock(), AsyncMock(), AsyncMock())
    with pytest.raises(ValueError):
        svc._validar_transicion(EstadoTarea.resuelta, EstadoTarea.pendiente)


def test_validar_transicion_desde_cancelada_lanza_value_error():
    """TRIANGULATE: 'cancelada' también es terminal."""
    svc = TareaService(AsyncMock(), AsyncMock(), AsyncMock())
    with pytest.raises(ValueError):
        svc._validar_transicion(EstadoTarea.cancelada, EstadoTarea.en_progreso)


def test_validar_transicion_invalida_no_terminal():
    """TRIANGULATE: transición no permitida aunque no sea terminal."""
    svc = TareaService(AsyncMock(), AsyncMock(), AsyncMock())
    # pendiente → resuelta no está en TRANSICIONES["pendiente"]
    with pytest.raises(ValueError):
        svc._validar_transicion(EstadoTarea.pendiente, EstadoTarea.resuelta)


# ── Task 7.4: cambiar_estado por usuario no involucrado lanza PermissionError ──


async def test_cambiar_estado_usuario_no_involucrado_lanza_permission_error():
    """RED: cambiar_estado por un extraño (no asignado_a, no asignado_por, no admin)."""
    usuario_id = uuid.uuid4()
    tarea_mock = _make_tarea(
        estado=EstadoTarea.pendiente,
        asignado_a=uuid.uuid4(),  # otro usuario
        asignado_por=uuid.uuid4(),  # otro usuario
    )
    svc = _make_service(tarea_get_by_id=tarea_mock)

    with pytest.raises(PermissionError):
        await svc.cambiar_estado(
            tarea_mock.tenant_id,
            tarea_mock.id,
            EstadoTarea.en_progreso,
            usuario_id,
            ["TUTOR"],  # rol sin privilegios de admin
        )


async def test_cambiar_estado_coordinador_puede_aunque_no_involucrado():
    """TRIANGULATE: COORDINADOR puede cambiar estado sin ser involucrado."""
    usuario_id = uuid.uuid4()
    tarea_mock = _make_tarea(
        estado=EstadoTarea.pendiente,
        asignado_a=uuid.uuid4(),
        asignado_por=uuid.uuid4(),
    )
    svc = _make_service(tarea_get_by_id=tarea_mock)

    actualizada = _make_tarea(estado=EstadoTarea.en_progreso)
    svc.repo.update_estado.return_value = actualizada

    result = await svc.cambiar_estado(
        tarea_mock.tenant_id,
        tarea_mock.id,
        EstadoTarea.en_progreso,
        usuario_id,
        ["COORDINADOR"],
    )
    assert result is not None


# ── Task 7.5: listar_todas con rol no-admin lanza PermissionError ─────────────


async def test_listar_todas_rol_no_admin_lanza_permission_error():
    """RED: listar_todas con rol TUTOR o PROFESOR lanza PermissionError."""
    svc = _make_service()
    with pytest.raises(PermissionError):
        await svc.listar_todas(uuid.uuid4(), ["TUTOR"], {}, page=1, size=50)


async def test_listar_todas_rol_no_admin_profesor_lanza_permission_error():
    """TRIANGULATE: PROFESOR tampoco puede."""
    svc = _make_service()
    with pytest.raises(PermissionError):
        await svc.listar_todas(uuid.uuid4(), ["PROFESOR"], {}, page=1, size=50)


async def test_listar_todas_admin_puede():
    """TRIANGULATE: ADMIN sí puede."""
    svc = _make_service()
    svc.repo.list_all.return_value = ([], 0)

    result = await svc.listar_todas(uuid.uuid4(), ["ADMIN"], {}, page=1, size=50)
    assert result.total == 0
