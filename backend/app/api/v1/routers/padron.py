"""Router de padrón de alumnos.

Endpoints:
    POST   /api/v1/padron/{materia_id}/importar           — importar desde archivo
    POST   /api/v1/padron/{materia_id}/importar-moodle    — importar desde Moodle WS
    GET    /api/v1/padron/{materia_id}/activo             — ver padrón activo
    GET    /api/v1/padron/{materia_id}/versiones          — historial de versiones
    DELETE /api/v1/padron/{materia_id}/activo             — vaciar padrón activo
    PUT    /api/v1/admin/moodle-config                    — configurar Moodle por tenant

Permisos:
    padron:importar → importar archivos y vaciar
    padron:leer     → leer versiones y entradas
    admin:config    → configurar Moodle
"""

import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.schemas.padron import (
    ImportarPadronMoodleRequest,
    ImportarResultadoOut,
    MoodleConfigRequest,
    VersionPadronDetalleOut,
    VersionPadronOut,
)
from app.services.padron_service import PadronService

router = APIRouter(prefix="/api/v1/padron", tags=["padron"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── POST /{materia_id}/importar ───────────────────────────────────────────────


@router.post(
    "/{materia_id}/importar",
    response_model=ImportarResultadoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("padron:importar"))],
)
async def importar_padron_archivo(
    materia_id: uuid.UUID,
    file: UploadFile = File(...),
    cohorte_id: uuid.UUID = Form(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Importar padrón desde archivo xlsx o csv."""
    file_bytes = await file.read()
    filename = file.filename or "padron"

    svc = PadronService(session=session, current_user=current_user, request=request)
    return await svc.importar_archivo(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        file_bytes=file_bytes,
        filename=filename,
    )


# ── POST /{materia_id}/importar-moodle ────────────────────────────────────────


@router.post(
    "/{materia_id}/importar-moodle",
    response_model=ImportarResultadoOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("padron:importar"))],
)
async def importar_padron_moodle(
    materia_id: uuid.UUID,
    body: ImportarPadronMoodleRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Importar padrón desde Moodle Web Services."""
    svc = PadronService(session=session, current_user=current_user, request=request)
    return await svc.importar_moodle(
        materia_id=materia_id,
        cohorte_id=body.cohorte_id,
        course_id=body.course_id,
    )


# ── GET /{materia_id}/activo ──────────────────────────────────────────────────


@router.get(
    "/{materia_id}/activo",
    response_model=VersionPadronDetalleOut,
    dependencies=[Depends(require_permission("padron:leer"))],
)
async def get_padron_activo(
    materia_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Obtener la versión activa del padrón con sus entradas (email descifrado)."""
    svc = PadronService(session=session, current_user=current_user)
    return await svc.get_activo(materia_id=materia_id)


# ── GET /{materia_id}/versiones ───────────────────────────────────────────────


@router.get(
    "/{materia_id}/versiones",
    response_model=List[VersionPadronOut],
    dependencies=[Depends(require_permission("padron:leer"))],
)
async def listar_versiones_padron(
    materia_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Listar historial de versiones del padrón (activas e inactivas)."""
    svc = PadronService(session=session, current_user=current_user)
    return await svc.listar_versiones(materia_id=materia_id)


# ── DELETE /{materia_id}/activo ───────────────────────────────────────────────


@router.delete(
    "/{materia_id}/activo",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("padron:importar"))],
)
async def vaciar_padron(
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Vaciar (soft-delete) el padrón activo. Solo quien lo cargó puede vaciarlo."""
    svc = PadronService(session=session, current_user=current_user, request=request)
    await svc.vaciar(materia_id=materia_id, cohorte_id=cohorte_id)


# ── PUT /admin/moodle-config ──────────────────────────────────────────────────


@admin_router.put(
    "/moodle-config",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:config"))],
)
async def upsert_moodle_config(
    body: MoodleConfigRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Guardar (o reemplazar) la configuración Moodle WS del tenant."""
    svc = PadronService(session=session, current_user=current_user)
    await svc.upsert_moodle_config(
        moodle_url=body.moodle_url,
        moodle_token=body.moodle_token,
    )
    return {"status": "ok"}
