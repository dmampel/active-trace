"""Router de mensajería interna / inbox (C-20).

Endpoints bajo /api/v1/inbox:
- GET  /                       → 200 listar hilos recibidos
- GET  /{hilo_id}              → 200 leer hilo y marcar mensajes como leídos
- POST /{hilo_id}/responder    → 201 agregar mensaje de respuesta
- POST /                       → 201 crear nuevo hilo con primer mensaje

Guard: require_permission('inbox:usar') en todos los endpoints.
Identidad SIEMPRE desde el JWT — nunca de parámetros de request.
Hilo ajeno → 404 (no filtra existencia).
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.schemas.mensajeria import (
    HiloConMensajesRead,
    HiloRead,
    MensajeRead,
    NuevoHiloCreate,
    RespuestaCreate,
)
from app.services.inbox_service import InboxService

router = APIRouter(prefix="/api/v1/inbox", tags=["inbox"])

_PERM = "inbox:usar"


async def _svc(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InboxService:
    return InboxService(db, current_user)


@router.get(
    "",
    response_model=List[HiloRead],
    dependencies=[Depends(require_permission(_PERM))],
)
async def listar_inbox(svc: InboxService = Depends(_svc)):
    """Lista los hilos donde el usuario del JWT es destinatario."""
    return await svc.listar_inbox()


@router.get(
    "/{hilo_id}",
    response_model=HiloConMensajesRead,
    dependencies=[Depends(require_permission(_PERM))],
)
async def leer_hilo(hilo_id: uuid.UUID, svc: InboxService = Depends(_svc)):
    """Lee un hilo y sus mensajes (ordenados). Marca como leídos los del usuario.

    Si el usuario no participa o el hilo es de otro tenant → 404.
    """
    return await svc.leer_hilo(hilo_id)


@router.post(
    "/{hilo_id}/responder",
    response_model=MensajeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(_PERM))],
)
async def responder_hilo(
    hilo_id: uuid.UUID,
    body: RespuestaCreate,
    svc: InboxService = Depends(_svc),
):
    """Agrega un mensaje de respuesta al hilo.

    autor_id desde JWT. Hilo ajeno → 404.
    """
    return await svc.responder_hilo(hilo_id, body.cuerpo)


@router.post(
    "",
    response_model=HiloRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(_PERM))],
)
async def crear_hilo(body: NuevoHiloCreate, svc: InboxService = Depends(_svc)):
    """Crea un nuevo hilo con su primer mensaje.

    destinatario_id debe ser un usuario activo del mismo tenant → 404 si no.
    """
    return await svc.crear_hilo(body.destinatario_id, body.asunto, body.cuerpo)
