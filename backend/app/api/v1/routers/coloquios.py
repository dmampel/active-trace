"""Router de coloquios y evaluaciones (C-14).

Endpoints:
    POST   /api/v1/coloquios                    → EvaluacionRead (201)
    GET    /api/v1/coloquios                    → list[EvaluacionRead]
    GET    /api/v1/coloquios/metricas           → MetricasColoquioRead
    GET    /api/v1/coloquios/{id}               → EvaluacionRead
    PUT    /api/v1/coloquios/{id}               → EvaluacionRead
    DELETE /api/v1/coloquios/{id}               → 200
    POST   /api/v1/coloquios/{id}/alumnos       → EvaluacionAlumnoImportResult
    POST   /api/v1/coloquios/{id}/reservar      → ReservaEvaluacionRead (201)
    DELETE /api/v1/coloquios/{id}/reservar      → 200
    GET    /api/v1/coloquios/{id}/agenda        → list[AgendaEntradaRead]
    POST   /api/v1/coloquios/{id}/resultados    → ResultadoEvaluacionRead (201)
    GET    /api/v1/coloquios/{id}/resultados    → list[ResultadoEvaluacionRead]

Permisos (RBAC fail-closed):
    coloquios:gestionar → POST/PUT/DELETE convocatorias, importar alumnos, registrar resultados
    coloquios:ver       → GET convocatorias, métricas, agenda, resultados
    coloquios:reservar  → POST/DELETE /reservar (solo ALUMNO)

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.evaluacion import (
    AgendaEntradaRead,
    EvaluacionAlumnoImportRequest,
    EvaluacionAlumnoImportResult,
    EvaluacionCreate,
    EvaluacionRead,
    EvaluacionUpdate,
    MetricasColoquioRead,
    ReservaEvaluacionCreate,
    ReservaEvaluacionRead,
    ResultadoEvaluacionRead,
    ResultadoEvaluacionUpsert,
)
from app.services.evaluacion_service import EvaluacionService

router = APIRouter(prefix="/api/v1/coloquios", tags=["coloquios"])


# ── Dependency factory ─────────────────────────────────────────────────────────


def _get_evaluacion_service(db: AsyncSession = Depends(get_db)) -> EvaluacionService:
    evaluacion_repo = EvaluacionRepository(db)
    usuario_repo = UsuarioRepository(db)
    return EvaluacionService(evaluacion_repo=evaluacion_repo, usuario_repo=usuario_repo)


# ── POST /coloquios ────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=EvaluacionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("coloquios:gestionar"))],
)
async def crear_convocatoria(
    data: EvaluacionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
    db: AsyncSession = Depends(get_db),
):
    """Crea una convocatoria de coloquio/evaluación.

    tenant_id tomado exclusivamente del JWT.
    """
    result = await svc.crear(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return result


# ── GET /coloquios ─────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[EvaluacionRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("coloquios:ver"))],
)
async def listar_convocatorias(
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
):
    """Lista convocatorias activas del tenant."""
    return await svc.listar(tenant_id=current_user.tenant_id)


# ── GET /coloquios/metricas ────────────────────────────────────────────────────
# IMPORTANTE: esta ruta debe ir ANTES de /{id} para evitar que "metricas" sea
# interpretada como un UUID.


@router.get(
    "/metricas",
    response_model=MetricasColoquioRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("coloquios:ver"))],
)
async def obtener_metricas(
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
):
    """Retorna métricas del módulo de coloquios para el tenant."""
    return await svc.get_metricas(tenant_id=current_user.tenant_id)


# ── GET /coloquios/{id} ────────────────────────────────────────────────────────


@router.get(
    "/{evaluacion_id}",
    response_model=EvaluacionRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("coloquios:ver"))],
)
async def obtener_convocatoria(
    evaluacion_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
):
    """Obtiene una convocatoria por ID."""
    return await svc.obtener(evaluacion_id, tenant_id=current_user.tenant_id)


# ── PUT /coloquios/{id} ────────────────────────────────────────────────────────


@router.put(
    "/{evaluacion_id}",
    response_model=EvaluacionRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("coloquios:gestionar"))],
)
async def actualizar_convocatoria(
    evaluacion_id: uuid.UUID,
    data: EvaluacionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza una convocatoria."""
    result = await svc.actualizar(evaluacion_id, tenant_id=current_user.tenant_id, data=data)
    await db.commit()
    return result


# ── DELETE /coloquios/{id} ─────────────────────────────────────────────────────


@router.delete(
    "/{evaluacion_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("coloquios:gestionar"))],
)
async def eliminar_convocatoria(
    evaluacion_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete de una convocatoria."""
    await svc.eliminar(evaluacion_id, tenant_id=current_user.tenant_id)
    await db.commit()
    return {"ok": True}


# ── POST /coloquios/{id}/alumnos ───────────────────────────────────────────────


@router.post(
    "/{evaluacion_id}/alumnos",
    response_model=EvaluacionAlumnoImportResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("coloquios:gestionar"))],
)
async def importar_alumnos(
    evaluacion_id: uuid.UUID,
    data: EvaluacionAlumnoImportRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
    db: AsyncSession = Depends(get_db),
):
    """Importa lista de alumnos habilitados a una convocatoria."""
    result = await svc.importar_alumnos(
        evaluacion_id,
        tenant_id=current_user.tenant_id,
        alumno_ids=data.alumno_ids,
    )
    await db.commit()
    return result


# ── POST /coloquios/{id}/reservar ──────────────────────────────────────────────


@router.post(
    "/{evaluacion_id}/reservar",
    response_model=ReservaEvaluacionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("coloquios:reservar"))],
)
async def reservar_turno(
    evaluacion_id: uuid.UUID,
    data: ReservaEvaluacionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
    db: AsyncSession = Depends(get_db),
):
    """Reserva un turno de coloquio (solo ALUMNO habilitado).

    alumno_id tomado del JWT — nunca del body.
    """
    result = await svc.reservar_turno(
        evaluacion_id,
        alumno_id=current_user.id,
        tenant_id=current_user.tenant_id,
        fecha=data.fecha,
    )
    await db.commit()
    return result


# ── DELETE /coloquios/{id}/reservar ───────────────────────────────────────────


@router.delete(
    "/{evaluacion_id}/reservar",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("coloquios:reservar"))],
)
async def cancelar_reserva(
    evaluacion_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
    db: AsyncSession = Depends(get_db),
):
    """Cancela la reserva activa del alumno autenticado.

    alumno_id tomado del JWT — nunca del body ni del path.
    """
    await svc.cancelar_reserva(
        evaluacion_id,
        alumno_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    await db.commit()
    return {"ok": True}


# ── GET /coloquios/{id}/agenda ─────────────────────────────────────────────────


@router.get(
    "/{evaluacion_id}/agenda",
    response_model=list[AgendaEntradaRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("coloquios:ver"))],
)
async def obtener_agenda(
    evaluacion_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
):
    """Agenda de reservas activas de una convocatoria."""
    return await svc.get_agenda(evaluacion_id, tenant_id=current_user.tenant_id)


# ── POST /coloquios/{id}/resultados ───────────────────────────────────────────


@router.post(
    "/{evaluacion_id}/resultados",
    response_model=ResultadoEvaluacionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("coloquios:gestionar"))],
)
async def registrar_resultado(
    evaluacion_id: uuid.UUID,
    data: ResultadoEvaluacionUpsert,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
    db: AsyncSession = Depends(get_db),
):
    """Registra o actualiza la nota final de un alumno (upsert)."""
    result = await svc.upsert_resultado(
        evaluacion_id,
        tenant_id=current_user.tenant_id,
        data=data,
    )
    await db.commit()
    return result


# ── GET /coloquios/{id}/resultados ────────────────────────────────────────────


@router.get(
    "/{evaluacion_id}/resultados",
    response_model=list[ResultadoEvaluacionRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("coloquios:ver"))],
)
async def listar_resultados(
    evaluacion_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EvaluacionService = Depends(_get_evaluacion_service),
):
    """Lista todos los resultados de una convocatoria."""
    return await svc.get_resultados(evaluacion_id, tenant_id=current_user.tenant_id)
