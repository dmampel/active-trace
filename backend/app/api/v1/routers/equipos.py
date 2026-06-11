"""Router de operaciones colectivas sobre equipos docentes (C-08).

Endpoints bajo /api/v1/equipos:
- GET    /mis-asignaciones   → 200 vista propia del docente
- GET    /usuarios/buscar    → 200 autocompletado para asignación masiva
- POST   /masiva             → 201 asignación en bloque
- POST   /clonar             → 201 clonar equipo entre cohortes
- PATCH  /vigencia           → 200 actualizar fechas del equipo
- GET    /exportar           → 200 CSV descargable del plantel

Guards:
- equipos:read_own → mis-asignaciones
- equipos:manage   → usuarios/buscar, masiva, clonar, vigencia
- equipos:export   → exportar

Identidad/tenant SIEMPRE desde get_current_user (JWT).
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.schemas.equipo import (
    AsignacionDetalleResponse,
    AsignacionMasivaRequest,
    AsignacionMasivaResponse,
    ClonarEquipoRequest,
    ClonarEquipoResponse,
    UsuarioBusquedaResponse,
    VigenciaEquipoRequest,
    VigenciaEquipoResponse,
)
from app.services.equipo_service import EquipoService

router = APIRouter(prefix="/api/v1/equipos", tags=["equipos"])


async def _svc(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EquipoService:
    return EquipoService(db, current_user, request)


# ── GET /mis-asignaciones ─────────────────────────────────────────────────────

@router.get(
    "/mis-asignaciones",
    response_model=List[AsignacionDetalleResponse],
    dependencies=[Depends(require_permission("equipos:read_own"))],
)
async def get_mis_asignaciones(
    estado_vigencia: Optional[str] = None,
    materia_id: Optional[uuid.UUID] = None,
    rol: Optional[str] = None,
    carrera_id: Optional[uuid.UUID] = None,
    cohorte_id: Optional[uuid.UUID] = None,
    svc: EquipoService = Depends(_svc),
):
    return await svc.mis_asignaciones(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        carrera_id=carrera_id,
        rol=rol,
        estado_vigencia=estado_vigencia,
    )


# ── GET /usuarios/buscar ──────────────────────────────────────────────────────

@router.get(
    "/usuarios/buscar",
    response_model=List[UsuarioBusquedaResponse],
    dependencies=[Depends(require_permission("equipos:manage"))],
)
async def buscar_usuarios(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=20, le=50, ge=1),
    svc: EquipoService = Depends(_svc),
):
    return await svc.buscar_usuarios(q=q, limit=limit)


# ── POST /masiva ──────────────────────────────────────────────────────────────

@router.post(
    "/masiva",
    response_model=AsignacionMasivaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("equipos:manage"))],
)
async def asignacion_masiva(
    body: AsignacionMasivaRequest,
    svc: EquipoService = Depends(_svc),
):
    return await svc.asignacion_masiva(body)


# ── POST /clonar ──────────────────────────────────────────────────────────────

@router.post(
    "/clonar",
    response_model=ClonarEquipoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("equipos:manage"))],
)
async def clonar_equipo(
    body: ClonarEquipoRequest,
    svc: EquipoService = Depends(_svc),
):
    return await svc.clonar_equipo(body)


# ── PATCH /vigencia ───────────────────────────────────────────────────────────

@router.patch(
    "/vigencia",
    response_model=VigenciaEquipoResponse,
    dependencies=[Depends(require_permission("equipos:manage"))],
)
async def actualizar_vigencia(
    body: VigenciaEquipoRequest,
    svc: EquipoService = Depends(_svc),
):
    return await svc.actualizar_vigencia(body)


# ── GET /exportar ─────────────────────────────────────────────────────────────

@router.get(
    "/exportar",
    dependencies=[Depends(require_permission("equipos:export"))],
)
async def exportar_equipo(svc: EquipoService = Depends(_svc)) -> StreamingResponse:
    return await svc.exportar_csv()
