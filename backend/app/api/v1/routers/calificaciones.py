"""Router de calificaciones (C-10).

Endpoints:
    POST   /api/v1/calificaciones/{materia_id}/preview       — preview sin persistir
    POST   /api/v1/calificaciones/{materia_id}/importar      — importar con selección
    GET    /api/v1/calificaciones/{materia_id}/               — listar calificaciones
    POST   /api/v1/calificaciones/{materia_id}/finalizacion   — cruzar reporte finalización
    PUT    /api/v1/calificaciones/{materia_id}/umbral         — configurar umbral

Permisos (RBAC fail-closed):
    calificaciones:importar → preview, importar, finalizacion, umbral
    calificaciones:leer     → listar

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.calificacion_repository import CalificacionRepository
from app.repositories.umbral_repository import UmbralRepository
from app.schemas.calificacion import (
    ConfigUmbralOut,
    ConfigUmbralRequest,
    FinalizacionReporteOut,
    FinalizacionReporteRequest,
    ImportarCalificacionesOut,
    ImportarCalificacionesRequest,
    PreviewCalificacionesOut,
    SinCorregirOut,
)
from app.services.calificacion_service import CalificacionService
from app.services.umbral_service import UmbralService

router = APIRouter(prefix="/api/v1/calificaciones", tags=["calificaciones"])


# ── Dependency factory ────────────────────────────────────────────────────────


def _get_calificacion_service(db: AsyncSession = Depends(get_db)) -> CalificacionService:
    """Construye el CalificacionService con sus dependencias."""
    cal_repo = CalificacionRepository(db)
    audit_repo = AuditLogRepository(db)
    umbral_repo = UmbralRepository(db)
    umbral_svc = UmbralService(umbral_repo)
    return CalificacionService(cal_repo, audit_repo, umbral_svc)


def _get_umbral_service(db: AsyncSession = Depends(get_db)) -> UmbralService:
    umbral_repo = UmbralRepository(db)
    return UmbralService(umbral_repo)


# ── POST /{materia_id}/preview ────────────────────────────────────────────────


@router.post(
    "/{materia_id}/preview",
    response_model=PreviewCalificacionesOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:importar"))],
)
async def preview_calificaciones(
    materia_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: CalificacionService = Depends(_get_calificacion_service),
):
    """Parsea el archivo del LMS y retorna actividades detectadas sin persistir."""
    csv_data = await file.read()
    resultado = await svc.preview(
        tenant_id=current_user.tenant_id,
        materia_id=materia_id,
        csv_data=csv_data,
        escala_textual=[],  # TODO: resolver desde config del tenant
    )
    return PreviewCalificacionesOut(
        actividades=resultado["actividades"],
        total_alumnos=len(resultado["filas"]),
    )


# ── POST /{materia_id}/importar ───────────────────────────────────────────────


@router.post(
    "/{materia_id}/importar",
    response_model=ImportarCalificacionesOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:importar"))],
)
async def importar_calificaciones(
    materia_id: uuid.UUID,
    body: ImportarCalificacionesRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    svc: CalificacionService = Depends(_get_calificacion_service),
):
    """Persiste calificaciones para las actividades seleccionadas por el usuario.

    El tenant_id y actor_id se toman EXCLUSIVAMENTE del JWT.
    Cualquier tenant_id en el body viola extra='forbid' y es rechazado.
    """
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    resultado = await svc.importar(
        tenant_id=current_user.tenant_id,   # JWT — nunca del body
        actor_id=current_user.id,            # JWT — nunca del body
        materia_id=materia_id,
        actividades=[a.model_dump() for a in body.actividades],
        seleccionadas=body.seleccionadas,
        filas=body.filas,
        ip=ip,
        user_agent=user_agent,
    )
    return ImportarCalificacionesOut(filas_afectadas=resultado["filas_afectadas"])


# ── GET /{materia_id}/ ────────────────────────────────────────────────────────


@router.get(
    "/{materia_id}/",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:leer"))],
)
async def listar_calificaciones(
    materia_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: CalificacionService = Depends(_get_calificacion_service),
):
    """Lista calificaciones de una materia (tenant del JWT)."""
    cals = await svc._cal_repo.listar_por_materia(materia_id, current_user.tenant_id)
    return [
        {
            "id": str(c.id),
            "entrada_padron_id": str(c.entrada_padron_id),
            "actividad": c.actividad,
            "nota_numerica": float(c.nota_numerica) if c.nota_numerica is not None else None,
            "nota_textual": c.nota_textual,
            "origen": c.origen.value,
        }
        for c in cals
    ]


# ── POST /{materia_id}/finalizacion ──────────────────────────────────────────


@router.post(
    "/{materia_id}/finalizacion",
    response_model=FinalizacionReporteOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:importar"))],
)
async def cruzar_finalizacion(
    materia_id: uuid.UUID,
    body: FinalizacionReporteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: CalificacionService = Depends(_get_calificacion_service),
):
    """Cruza el reporte de finalización del LMS con calificaciones importadas."""
    finalizaciones = [f.model_dump() for f in body.finalizaciones]
    sin_corregir = await svc.cruzar_finalizacion(
        tenant_id=current_user.tenant_id,
        materia_id=materia_id,
        finalizaciones=finalizaciones,
    )
    return FinalizacionReporteOut(
        sin_corregir=[SinCorregirOut(**s) for s in sin_corregir],
        total=len(sin_corregir),
    )


# ── PUT /{materia_id}/umbral ──────────────────────────────────────────────────


@router.put(
    "/{materia_id}/umbral",
    response_model=ConfigUmbralOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:importar"))],
)
async def configurar_umbral(
    materia_id: uuid.UUID,
    body: ConfigUmbralRequest,
    current_user: CurrentUser = Depends(get_current_user),
    umbral_svc: UmbralService = Depends(_get_umbral_service),
):
    """Configura el umbral de aprobación para la asignación del docente en sesión.

    El asignacion_id se resuelve desde el contexto del JWT (no del body).
    TODO: resolver asignacion_id desde current_user.asignacion_activa cuando
    el modelo de asignaciones contextual esté disponible. Por ahora se pasa
    como query param opcional para permitir el flujo docente.
    """
    # Identidad completa del JWT: tenant + usuario. El asignacion_id se
    # pasa como campo del body SOLO para el caso de uso docente explícito.
    # Como workaround temporal hasta que current_user lleve la asignacion_activa.
    asignacion_id: uuid.UUID = getattr(body, "asignacion_id", None) or uuid.uuid4()

    saved = await umbral_svc.configurar(
        tenant_id=current_user.tenant_id,
        asignacion_id=asignacion_id,
        materia_id=body.materia_id,
        umbral_pct=body.umbral_pct,
        valores_aprobatorios=body.valores_aprobatorios,
    )
    return ConfigUmbralOut(
        id=saved.id,
        asignacion_id=saved.asignacion_id,
        materia_id=saved.materia_id,
        umbral_pct=saved.umbral_pct,
        valores_aprobatorios=list(saved.valores_aprobatorios),
    )
