"""Router de comunicaciones salientes (C-12).

Endpoints:
    POST /api/v1/comunicaciones/preview            → ComunicacionPreviewResponse
    POST /api/v1/comunicaciones/enviar             → ComunicacionEnviarResponse
    POST /api/v1/comunicaciones/lotes/{id}/aprobar → LoteAccionResponse
    POST /api/v1/comunicaciones/lotes/{id}/cancelar→ LoteAccionResponse
    POST /api/v1/comunicaciones/{id}/cancelar      → ComunicacionResponse
    GET  /api/v1/comunicaciones/                   → list[ComunicacionResponse]

Permisos (RBAC fail-closed):
    comunicacion:enviar  → POST /preview, POST /enviar, POST /{id}/cancelar
    comunicacion:aprobar → POST /lotes/{id}/aprobar, POST /lotes/{id}/cancelar
    comunicacion:ver     → GET /

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.core.security import AES256GCMCipher, derive_encryption_key
from app.models.comunicacion import EstadoComunicacion
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.schemas.comunicacion import (
    ComunicacionEnviarRequest,
    ComunicacionEnviarResponse,
    ComunicacionPreviewRequest,
    ComunicacionPreviewResponse,
    ComunicacionResponse,
    LoteAccionRequest,
    LoteAccionResponse,
)
from app.services.comunicacion_service import ComunicacionService

router = APIRouter(prefix="/api/v1/comunicaciones", tags=["comunicaciones"])


# ── Dependency factory ────────────────────────────────────────────────────────


def _get_cipher() -> AES256GCMCipher:
    settings = get_settings()
    return AES256GCMCipher(derive_encryption_key(settings.encryption_key))


def _get_comunicacion_service(db: AsyncSession = Depends(get_db)) -> ComunicacionService:
    cipher = _get_cipher()
    repo = ComunicacionRepository(db, cipher)
    audit_repo = AuditLogRepository(db)
    return ComunicacionService(repo=repo, audit_log_repo=audit_repo)


# ── POST /preview ─────────────────────────────────────────────────────────────


@router.post(
    "/preview",
    response_model=ComunicacionPreviewResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("comunicacion:enviar"))],
)
async def preview_comunicacion(
    request: ComunicacionPreviewRequest,
    _current_user: CurrentUser = Depends(get_current_user),
    svc: ComunicacionService = Depends(_get_comunicacion_service),
):
    """Previsualiza un mensaje con variables resueltas. No persiste."""
    return await svc.preview(request)


# ── POST /enviar ──────────────────────────────────────────────────────────────


@router.post(
    "/enviar",
    response_model=ComunicacionEnviarResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("comunicacion:enviar"))],
)
async def enviar_comunicacion(
    request: ComunicacionEnviarRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ComunicacionService = Depends(_get_comunicacion_service),
):
    """Encola mensajes en estado Pendiente."""
    return await svc.encolar(
        request,
        usuario_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )


# ── POST /lotes/{lote_id}/aprobar ─────────────────────────────────────────────


@router.post(
    "/lotes/{lote_id}/aprobar",
    response_model=LoteAccionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("comunicacion:aprobar"))],
)
async def aprobar_lote(
    lote_id: uuid.UUID,
    _request: LoteAccionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ComunicacionService = Depends(_get_comunicacion_service),
):
    """Aprueba todos los mensajes Pendiente de un lote."""
    return await svc.aprobar_lote(
        lote_id=lote_id,
        tenant_id=current_user.tenant_id,
        aprobador_id=current_user.id,
    )


# ── POST /lotes/{lote_id}/cancelar ────────────────────────────────────────────


@router.post(
    "/lotes/{lote_id}/cancelar",
    response_model=LoteAccionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("comunicacion:aprobar"))],
)
async def cancelar_lote(
    lote_id: uuid.UUID,
    _request: LoteAccionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ComunicacionService = Depends(_get_comunicacion_service),
):
    """Cancela todos los mensajes Pendiente de un lote."""
    return await svc.cancelar_lote(
        lote_id=lote_id,
        tenant_id=current_user.tenant_id,
        usuario_id=current_user.id,
    )


# ── POST /{comunicacion_id}/cancelar ─────────────────────────────────────────


@router.post(
    "/{comunicacion_id}/cancelar",
    response_model=ComunicacionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("comunicacion:enviar"))],
)
async def cancelar_comunicacion(
    comunicacion_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ComunicacionService = Depends(_get_comunicacion_service),
):
    """Cancela un mensaje individual en estado Pendiente."""
    return await svc.cancelar_individual(
        comunicacion_id=comunicacion_id,
        tenant_id=current_user.tenant_id,
        usuario_id=current_user.id,
    )


# ── GET / ────────────────────────────────────────────────────────────────────


@router.get(
    "/",
    response_model=List[ComunicacionResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("comunicacion:ver"))],
)
async def listar_comunicaciones(
    estado: Optional[EstadoComunicacion] = Query(default=None),
    lote_id: Optional[uuid.UUID] = Query(default=None),
    materia_id: Optional[uuid.UUID] = Query(default=None),
    desde: Optional[datetime] = Query(default=None),
    hasta: Optional[datetime] = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ComunicacionService = Depends(_get_comunicacion_service),
):
    """Lista mensajes del tenant con filtros opcionales."""
    return await svc.listar(
        tenant_id=current_user.tenant_id,
        estado=estado,
        lote_id=lote_id,
        materia_id=materia_id,
        desde=desde,
        hasta=hasta,
    )
