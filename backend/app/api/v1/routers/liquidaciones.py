"""Router de liquidaciones y honorarios (C-18).

Endpoints:
    POST   /api/v1/liquidaciones/calcular                → LiquidacionCalcularResponse (200)  [liquidaciones:calcular]
    GET    /api/v1/liquidaciones                         → LiquidacionVistaPeriodo     (200)  [liquidaciones:ver]
    GET    /api/v1/liquidaciones/salarios                → GrillaSalarialResponse      (200)  [liquidaciones:ver]
    POST   /api/v1/liquidaciones/salarios/base           → SalarioBaseResponse         (201)  [liquidaciones:configurar-salarios]
    PATCH  /api/v1/liquidaciones/salarios/base/{id}      → SalarioBaseResponse         (200)  [liquidaciones:configurar-salarios]
    POST   /api/v1/liquidaciones/salarios/plus           → SalarioPlusResponse         (201)  [liquidaciones:configurar-salarios]
    PATCH  /api/v1/liquidaciones/salarios/plus/{id}      → SalarioPlusResponse         (200)  [liquidaciones:configurar-salarios]
    GET    /api/v1/liquidaciones/{id}                    → LiquidacionDetalle          (200)  [liquidaciones:ver]
    POST   /api/v1/liquidaciones/{id}/cerrar             → list[LiquidacionResponse]   (200)  [liquidaciones:cerrar]

IMPORTANTE: las rutas fijas (/calcular, /salarios) deben ir ANTES de /{id}
para que FastAPI no las interprete como UUIDs.

Permisos (RBAC fail-closed):
    liquidaciones:ver               → GET endpoints
    liquidaciones:calcular          → POST /calcular
    liquidaciones:cerrar            → POST /{id}/cerrar
    liquidaciones:configurar-salarios → grilla salarial (POST/PATCH)

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.permissions import require_permission
from app.models.liquidacion import EstadoLiquidacion
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.liquidacion_repository import (
    FacturaRepository,
    LiquidacionRepository,
    SalarioBaseRepository,
    SalarioPlusRepository,
)
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.liquidacion import (
    GrillaSalarialResponse,
    LiquidacionCalcularRequest,
    LiquidacionCalcularResponse,
    LiquidacionDetalle,
    LiquidacionResponse,
    LiquidacionVistaPeriodo,
    SalarioBaseCreate,
    SalarioBaseResponse,
    SalarioBaseUpdate,
    SalarioPlusCreate,
    SalarioPlusResponse,
    SalarioPlusUpdate,
)
from app.services.liquidacion_service import LiquidacionService
from app.services.salario_service import SalarioService

router = APIRouter(prefix="/api/v1/liquidaciones", tags=["liquidaciones"])


# ── Dependency factories ───────────────────────────────────────────────────────


def _get_liq_service(db: AsyncSession = Depends(get_db)) -> LiquidacionService:
    return LiquidacionService(
        session=db,
        liq_repo=LiquidacionRepository(db),
        salario_base_repo=SalarioBaseRepository(db),
        salario_plus_repo=SalarioPlusRepository(db),
        asignacion_repo=AsignacionRepository(db),
        usuario_repo=UsuarioRepository(db),
        audit_repo=AuditLogRepository(db),
    )


def _get_salario_service(db: AsyncSession = Depends(get_db)) -> SalarioService:
    return SalarioService(
        base_repo=SalarioBaseRepository(db),
        plus_repo=SalarioPlusRepository(db),
    )


# ── POST /liquidaciones/calcular ──────────────────────────────────────────────


@router.post(
    "/calcular",
    response_model=LiquidacionCalcularResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("liquidaciones:calcular"))],
)
async def calcular_periodo(
    data: LiquidacionCalcularRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: LiquidacionService = Depends(_get_liq_service),
    db: AsyncSession = Depends(get_db),
):
    """Calcula o recalcula las liquidaciones para todos los docentes activos de una cohorte."""
    result = await svc.calcular_periodo(current_user.tenant_id, data.cohorte_id, data.periodo)
    await db.commit()
    return result


# ── GET /liquidaciones/salarios ───────────────────────────────────────────────


@router.get(
    "/salarios",
    response_model=GrillaSalarialResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("liquidaciones:ver"))],
)
async def get_grilla_salarial(
    current_user: CurrentUser = Depends(get_current_user),
    svc: SalarioService = Depends(_get_salario_service),
):
    """Retorna la grilla salarial completa (base + plus) del tenant."""
    return await svc.list_grilla(current_user.tenant_id)


# ── POST /liquidaciones/salarios/base ─────────────────────────────────────────


@router.post(
    "/salarios/base",
    response_model=SalarioBaseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("liquidaciones:configurar-salarios"))],
)
async def create_salario_base(
    data: SalarioBaseCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: SalarioService = Depends(_get_salario_service),
    db: AsyncSession = Depends(get_db),
):
    """Crea un salario base. Rechaza con 409 si hay solapamiento de vigencia."""
    result = await svc.create_base(current_user.tenant_id, data)
    await db.commit()
    return result


# ── PATCH /liquidaciones/salarios/base/{id} ───────────────────────────────────


@router.patch(
    "/salarios/base/{salario_id}",
    response_model=SalarioBaseResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("liquidaciones:configurar-salarios"))],
)
async def update_salario_base(
    salario_id: uuid.UUID,
    data: SalarioBaseUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: SalarioService = Depends(_get_salario_service),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.update_base(current_user.tenant_id, salario_id, data)
    await db.commit()
    return result


# ── POST /liquidaciones/salarios/plus ─────────────────────────────────────────


@router.post(
    "/salarios/plus",
    response_model=SalarioPlusResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("liquidaciones:configurar-salarios"))],
)
async def create_salario_plus(
    data: SalarioPlusCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: SalarioService = Depends(_get_salario_service),
    db: AsyncSession = Depends(get_db),
):
    """Crea un plus salarial para una clave × rol."""
    result = await svc.create_plus(current_user.tenant_id, data)
    await db.commit()
    return result


# ── PATCH /liquidaciones/salarios/plus/{id} ───────────────────────────────────


@router.patch(
    "/salarios/plus/{plus_id}",
    response_model=SalarioPlusResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("liquidaciones:configurar-salarios"))],
)
async def update_salario_plus(
    plus_id: uuid.UUID,
    data: SalarioPlusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: SalarioService = Depends(_get_salario_service),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.update_plus(current_user.tenant_id, plus_id, data)
    await db.commit()
    return result


# ── GET /liquidaciones ────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=LiquidacionVistaPeriodo,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("liquidaciones:ver"))],
)
async def get_liquidaciones(
    cohorte_id: uuid.UUID,
    periodo: str,
    estado: Optional[EstadoLiquidacion] = None,
    current_user: CurrentUser = Depends(get_current_user),
    svc: LiquidacionService = Depends(_get_liq_service),
):
    """Retorna la vista segmentada (general/nexo/facturantes + KPIs) para un período."""
    return await svc.get_vista_periodo(
        current_user.tenant_id, cohorte_id, periodo, estado
    )


# ── GET /liquidaciones/{id} — DEBE ir DESPUÉS de las rutas fijas ──────────────


@router.get(
    "/{liquidacion_id}",
    response_model=LiquidacionDetalle,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("liquidaciones:ver"))],
)
async def get_liquidacion_detalle(
    liquidacion_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: LiquidacionService = Depends(_get_liq_service),
):
    """Retorna el detalle de una liquidación, incluyendo comisiones y claves activas."""
    return await svc.get_detalle(current_user.tenant_id, liquidacion_id)


# ── POST /liquidaciones/{id}/cerrar ───────────────────────────────────────────


@router.post(
    "/{liquidacion_id}/cerrar",
    response_model=LiquidacionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("liquidaciones:cerrar"))],
)
async def cerrar_liquidacion(
    liquidacion_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: LiquidacionService = Depends(_get_liq_service),
    db: AsyncSession = Depends(get_db),
):
    """Cierra una liquidación individual. 409 si ya está cerrada."""
    result = await svc.cerrar_por_id(
        current_user.tenant_id, liquidacion_id, current_user.id
    )
    await db.commit()
    return result
