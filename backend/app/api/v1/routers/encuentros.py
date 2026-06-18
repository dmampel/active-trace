"""Router de encuentros sincrónicos (C-13).

Endpoints:
    POST  /api/v1/encuentros/slots                → SlotEncuentroResponse
    GET   /api/v1/encuentros/slots                → list[SlotEncuentroResponse]
    PATCH /api/v1/encuentros/instancias/{id}      → InstanciaEncuentroResponse
    GET   /api/v1/encuentros/admin                → list[InstanciaEncuentroResponse]
    GET   /api/v1/encuentros/html-block           → HTMLResponse

Permisos (RBAC fail-closed):
    encuentros:gestionar → POST /slots, GET /slots, PATCH /instancias/{id}, GET /html-block
    encuentros:ver_admin → GET /admin

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
asignacion_id en creación y listado propios: query param (no del body; el service
no lo acepta en el body — regla dura #8 se aplica al campo asignacion_id de Guardia).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.repositories.encuentro_repository import (
    InstanciaEncuentroRepository,
    SlotEncuentroRepository,
)
from app.schemas.encuentro import (
    InstanciaEncuentroResponse,
    InstanciaEncuentroUpdate,
    SlotEncuentroCreate,
    SlotEncuentroResponse,
)
from app.services.encuentro_service import EncuentrosService

router = APIRouter(prefix="/api/v1/encuentros", tags=["encuentros"])


# ── Dependency factory ─────────────────────────────────────────────────────────


def _get_encuentros_service(db: AsyncSession = Depends(get_db)) -> EncuentrosService:
    slot_repo = SlotEncuentroRepository(db)
    instancia_repo = InstanciaEncuentroRepository(db)
    return EncuentrosService(slot_repo=slot_repo, instancia_repo=instancia_repo)


# ── POST /slots ────────────────────────────────────────────────────────────────


@router.post(
    "/slots",
    response_model=SlotEncuentroResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("encuentros:gestionar"))],
)
async def crear_slot(
    data: SlotEncuentroCreate,
    asignacion_id: uuid.UUID = Query(..., description="ID de la asignación del docente"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: EncuentrosService = Depends(_get_encuentros_service),
    db: AsyncSession = Depends(get_db),
):
    """Crea un slot de encuentro y genera sus instancias (RN-13).

    asignacion_id es un query param que identifica la asignación del docente.
    tenant_id se toma exclusivamente del JWT.
    """
    result = await svc.crear_slot(
        data,
        asignacion_id=asignacion_id,
        tenant_id=current_user.tenant_id,
    )
    await db.commit()
    return result


# ── GET /slots ─────────────────────────────────────────────────────────────────


@router.get(
    "/slots",
    response_model=list[SlotEncuentroResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("encuentros:gestionar"))],
)
async def listar_slots_propios(
    asignacion_id: uuid.UUID = Query(..., description="ID de la asignación del docente"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: EncuentrosService = Depends(_get_encuentros_service),
):
    """Lista los slots de encuentro de la asignación con sus instancias."""
    return await svc.listar_slots_propios(
        asignacion_id=asignacion_id,
        tenant_id=current_user.tenant_id,
    )


# ── PATCH /instancias/{instancia_id} ──────────────────────────────────────────


@router.patch(
    "/instancias/{instancia_id}",
    response_model=InstanciaEncuentroResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("encuentros:gestionar"))],
)
async def editar_instancia(
    instancia_id: uuid.UUID,
    data: InstanciaEncuentroUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: EncuentrosService = Depends(_get_encuentros_service),
    db: AsyncSession = Depends(get_db),
):
    """Edita campos de una instancia individual sin tocar el slot ni otras instancias (RN-14)."""
    result = await svc.editar_instancia(
        instancia_id,
        data,
        tenant_id=current_user.tenant_id,
    )
    await db.commit()
    return result


# ── GET /admin ────────────────────────────────────────────────────────────────


@router.get(
    "/admin",
    response_model=list[InstanciaEncuentroResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("encuentros:ver_admin"))],
)
async def listar_admin(
    current_user: CurrentUser = Depends(get_current_user),
    svc: EncuentrosService = Depends(_get_encuentros_service),
):
    """Lista todas las instancias del tenant (COORDINADOR/ADMIN)."""
    return await svc.listar_admin(tenant_id=current_user.tenant_id)


# ── GET /html-block ───────────────────────────────────────────────────────────


@router.get(
    "/html-block",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("encuentros:gestionar"))],
)
async def html_block(
    asignacion_id: uuid.UUID = Query(..., description="ID de la asignación"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: EncuentrosService = Depends(_get_encuentros_service),
):
    """Genera bloque HTML con calendario de encuentros para embeber en el LMS."""
    html = await svc.generar_html_block(
        asignacion_id=asignacion_id,
        tenant_id=current_user.tenant_id,
    )
    return HTMLResponse(content=html)
