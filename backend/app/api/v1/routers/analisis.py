"""Router de análisis de atrasados (C-11).

Endpoints:
    GET  /api/v1/analisis/atrasados?materia_id=&actividades=    → AtrasadoResponse
    GET  /api/v1/analisis/ranking?materia_id=                   → RankingResponse
    GET  /api/v1/analisis/reporte?materia_id=                   → ReporteRapidoResponse
    GET  /api/v1/analisis/notas-finales?materia_id=&actividades= → NotaFinalResponse
    POST /api/v1/analisis/tp-sin-corregir?materia_id=           → list[TpPendienteItem]
    GET  /api/v1/analisis/tp-sin-corregir/export?materia_id=    → StreamingResponse CSV
    GET  /api/v1/analisis/monitor?materia_id=&...filtros...     → MonitorResponse

Permisos (RBAC fail-closed):
    atrasados:ver → todos los endpoints

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

from __future__ import annotations

import csv
import io
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.repositories.analisis_repository import AnalisisRepository
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.analisis import (
    AtrasadoItem,
    AtrasadoResponse,
    MonitorItem,
    MonitorResponse,
    NotaFinalItem,
    NotaFinalResponse,
    RankingItem,
    RankingResponse,
    ReporteRapidoResponse,
    ActividadMetrica,
    TpPendienteItem,
    MonitorFiltros,
)
from app.services.analisis_service import AnalisisService

router = APIRouter(prefix="/api/v1/analisis", tags=["analisis"])


# ── Dependency factory ────────────────────────────────────────────────────────


def _get_analisis_service(db: AsyncSession = Depends(get_db)) -> AnalisisService:
    return AnalisisService(
        analisis_repo=AnalisisRepository(db),
        asignacion_repo=AsignacionRepository(db),
        session=db,
    )


# ── GET /atrasados ────────────────────────────────────────────────────────────


@router.get(
    "/atrasados",
    response_model=AtrasadoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("atrasados:ver"))],
)
async def get_atrasados(
    materia_id: uuid.UUID = Query(...),
    actividades: List[str] = Query(default=[]),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnalisisService = Depends(_get_analisis_service),
):
    """Lista alumnos atrasados para la materia y actividades seleccionadas."""
    result = await svc.get_atrasados(
        materia_id=materia_id,
        actividades_seleccionadas=actividades,
        current_user=current_user,
    )
    return AtrasadoResponse(
        total_atrasados=result["total_atrasados"],
        items=[AtrasadoItem(**item) for item in result["items"]],
    )


# ── GET /ranking ──────────────────────────────────────────────────────────────


@router.get(
    "/ranking",
    response_model=RankingResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("atrasados:ver"))],
)
async def get_ranking(
    materia_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnalisisService = Depends(_get_analisis_service),
):
    """Ranking de alumnos por actividades aprobadas (RN-09)."""
    result = await svc.get_ranking(materia_id=materia_id, current_user=current_user)
    return RankingResponse(
        total=result["total"],
        items=[RankingItem(**item) for item in result["items"]],
    )


# ── GET /reporte ──────────────────────────────────────────────────────────────


@router.get(
    "/reporte",
    response_model=ReporteRapidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("atrasados:ver"))],
)
async def get_reporte_rapido(
    materia_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnalisisService = Depends(_get_analisis_service),
):
    """Métricas consolidadas de la materia."""
    result = await svc.get_reporte_rapido(materia_id=materia_id, current_user=current_user)
    return ReporteRapidoResponse(
        total_alumnos=result["total_alumnos"],
        total_atrasados=result["total_atrasados"],
        actividades_count=result["actividades_count"],
        metricas_por_actividad=[ActividadMetrica(**m) for m in result["metricas_por_actividad"]],
    )


# ── GET /notas-finales ────────────────────────────────────────────────────────


@router.get(
    "/notas-finales",
    response_model=NotaFinalResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("atrasados:ver"))],
)
async def get_notas_finales(
    materia_id: uuid.UUID = Query(...),
    actividades: List[str] = Query(default=[]),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnalisisService = Depends(_get_analisis_service),
):
    """Nota final por alumno sumando actividades seleccionadas."""
    result = await svc.get_notas_finales(
        materia_id=materia_id,
        actividades_seleccionadas=actividades,
        current_user=current_user,
    )
    return NotaFinalResponse(
        actividades_seleccionadas=result["actividades_seleccionadas"],
        items=[NotaFinalItem(**item) for item in result["items"]],
    )


# ── POST /tp-sin-corregir ─────────────────────────────────────────────────────


@router.post(
    "/tp-sin-corregir",
    response_model=list[TpPendienteItem],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("atrasados:ver"))],
)
async def detectar_tp_sin_corregir(
    materia_id: uuid.UUID = Query(...),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnalisisService = Depends(_get_analisis_service),
):
    """Sube el CSV de finalización del LMS y retorna TPs sin corrección textual."""
    csv_bytes = await file.read()
    pendientes = await svc.detectar_tp_sin_corregir(
        materia_id=materia_id,
        csv_bytes=csv_bytes,
        current_user=current_user,
    )
    return [TpPendienteItem(**p) for p in pendientes]


# ── GET /tp-sin-corregir/export ───────────────────────────────────────────────


@router.get(
    "/tp-sin-corregir/export",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("atrasados:ver"))],
)
async def export_notas_finales_csv(
    materia_id: uuid.UUID = Query(...),
    actividades: List[str] = Query(default=[]),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnalisisService = Depends(_get_analisis_service),
):
    """Exporta notas finales como CSV descargable (text/csv)."""
    result = await svc.get_notas_finales(
        materia_id=materia_id,
        actividades_seleccionadas=actividades,
        current_user=current_user,
    )
    items = result["items"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["entrada_padron_id", "apellidos", "nombre", "nota_final", "actividades_incluidas"])
    for item in items:
        writer.writerow([
            str(item["entrada_padron_id"]),
            item["apellidos"],
            item["nombre"],
            item["nota_final"],
            item["actividades_incluidas"],
        ])

    filename = f"notas_finales_{materia_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── GET /monitor ──────────────────────────────────────────────────────────────


@router.get(
    "/monitor",
    response_model=MonitorResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("atrasados:ver"))],
)
async def get_monitor(
    request: Request,
    materia_id: uuid.UUID = Query(...),
    comision: Optional[str] = Query(default=None),
    busqueda_libre: Optional[str] = Query(default=None),
    estado_actividad: Optional[str] = Query(default=None),
    alumno: Optional[str] = Query(default=None),
    actividad: Optional[str] = Query(default=None),
    min_actividades_cumplidas: Optional[int] = Query(default=None),
    fecha_desde: Optional[str] = Query(default=None),
    fecha_hasta: Optional[str] = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnalisisService = Depends(_get_analisis_service),
):
    """Monitor de alumnos con filtros. COORDINADOR/ADMIN genera auditoría."""
    # Construir objeto de filtros compatible con el service
    class _Filtros:
        pass

    filtros = _Filtros()
    filtros.comision = comision
    filtros.busqueda_libre = busqueda_libre
    filtros.estado_actividad = estado_actividad
    filtros.alumno = alumno
    filtros.actividad = actividad
    filtros.min_actividades_cumplidas = min_actividades_cumplidas
    filtros.fecha_desde = fecha_desde
    filtros.fecha_hasta = fecha_hasta

    result = await svc.get_monitor(
        materia_id=materia_id,
        current_user=current_user,
        filtros=filtros,
        request=request,
    )
    return MonitorResponse(
        total=result["total"],
        items=[MonitorItem(**item) for item in result["items"]],
    )
