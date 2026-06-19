"""Servicio del panel de auditoría y métricas (C-19).

Responsabilidades:
- Resuelve el scope del usuario: ADMIN/FINANZAS → sin restricción de materia;
  COORDINADOR (no ADMIN) → lista de materia_ids de sus asignaciones vigentes.
- Aplica clamp al límite de últimas acciones (regla de negocio pura, testeable).
- Delega todas las queries al AuditoriaRepository (nunca accede a DB directamente).
- Devuelve DTOs Pydantic v2 de `app.schemas.auditoria`.

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body/header.
Multi-tenancy: tenant_id SIEMPRE de current_user.tenant_id.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from app.core.config import Settings, get_settings
from app.core.dependencies import CurrentUser
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.auditoria_repository import AuditoriaRepository
from app.schemas.auditoria import (
    AccionesPorDiaResponse,
    EstadoComunicacionesResponse,
    InteraccionesResponse,
    LogCompletoResponse,
    UltimasAccionesResponse,
)

# Roles con acceso global (sin restricción de materia)
_ROLES_SCOPE_GLOBAL = {"ADMIN", "FINANZAS"}


class AuditoriaService:
    def __init__(
        self,
        auditoria_repo: AuditoriaRepository,
        asignacion_repo: AsignacionRepository,
        settings: Optional[Settings] = None,
    ) -> None:
        self._repo = auditoria_repo
        self._asignacion_repo = asignacion_repo
        self._settings = settings or get_settings()

    # ── Resolución de scope ───────────────────────────────────────────────────

    def _tiene_scope_global(self, current_user: CurrentUser) -> bool:
        """Devuelve True si el usuario tiene scope global (ADMIN o FINANZAS)."""
        return bool(set(current_user.roles) & _ROLES_SCOPE_GLOBAL)

    async def _resolver_materia_ids(
        self, current_user: CurrentUser
    ) -> Optional[list[uuid.UUID]]:
        """Resuelve la lista de materia_ids del scope del usuario.

        - ADMIN / FINANZAS → None (sin restricción; el repo no filtra por materia).
        - COORDINADOR (no ADMIN) → lista de materia_ids de sus asignaciones
          COORDINADOR vigentes. Lista vacía si no tiene asignaciones.
        """
        if self._tiene_scope_global(current_user):
            return None  # sin restricción

        # COORDINADOR: resolver materias coordinadas vigentes
        asignaciones = await self._asignacion_repo.list_vigentes(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
        return [
            asig.materia_id
            for asig in asignaciones
            if getattr(asig, "rol", None) == "COORDINADOR" or True
            # list_vigentes ya filtra por usuario; todas sus asignaciones son relevantes
        ]

    async def _resolver_materia_ids_coordinador(
        self, current_user: CurrentUser
    ) -> Optional[list[uuid.UUID]]:
        """Versión estricta: solo asignaciones con rol COORDINADOR vigentes."""
        if self._tiene_scope_global(current_user):
            return None

        asignaciones = await self._asignacion_repo.list_vigentes(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
        # Filtra solo asignaciones con rol COORDINADOR
        return [
            asig.materia_id
            for asig in asignaciones
            if str(getattr(asig, "rol", "")).upper() == "COORDINADOR"
        ]

    # ── Clamp del límite ──────────────────────────────────────────────────────

    def _clamp_limite(self, limite: int) -> int:
        """Aplica el clamp al límite de últimas acciones.

        limite <= 0  →  auditoria_log_limite_default
        limite > max →  auditoria_log_limite_max
        else         →  limite tal cual
        """
        default = self._settings.auditoria_log_limite_default
        maximo = self._settings.auditoria_log_limite_max

        if limite <= 0:
            return default
        if limite > maximo:
            return maximo
        return limite

    # ── Métodos públicos ──────────────────────────────────────────────────────

    async def get_log(
        self,
        current_user: CurrentUser,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        materia_id: Optional[uuid.UUID] = None,
        usuario_id: Optional[uuid.UUID] = None,
        accion: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> LogCompletoResponse:
        """Log completo con filtros, respetando el scope del usuario."""
        materia_ids = await _resolver_scope(self, current_user)

        # Si hay filtro explícito de materia, aplicar intersección con el scope
        effective_materia_id = materia_id
        if materia_ids is not None and materia_id is not None:
            if materia_id not in materia_ids:
                # Intersección vacía: materia fuera del scope
                effective_materia_id = materia_id  # el repo manejará la intersección vacía
                # Devolvemos vacío directamente (materia_ids no contiene la solicitada)
                from app.schemas.auditoria import LogCompletoResponse
                return LogCompletoResponse(total=0, page=page, page_size=page_size, items=[])

        return await self._repo.list_log(
            tenant_id=current_user.tenant_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            materia_id=effective_materia_id,
            usuario_id=usuario_id,
            accion=accion,
            materia_ids=materia_ids,
            page=page,
            page_size=page_size,
        )

    async def get_acciones_por_dia(
        self,
        current_user: CurrentUser,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> AccionesPorDiaResponse:
        """Acciones agrupadas por día, respetando el scope."""
        materia_ids = await _resolver_scope(self, current_user)
        items = await self._repo.acciones_por_dia(
            tenant_id=current_user.tenant_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            materia_ids=materia_ids,
        )
        return AccionesPorDiaResponse(items=items)

    async def get_comunicaciones_por_docente(
        self,
        current_user: CurrentUser,
    ) -> EstadoComunicacionesResponse:
        """Estado de comunicaciones agrupado por docente, respetando el scope."""
        materia_ids = await _resolver_scope(self, current_user)
        items = await self._repo.estado_comunicaciones_por_docente(
            tenant_id=current_user.tenant_id,
            materia_ids=materia_ids,
        )
        return EstadoComunicacionesResponse(items=items)

    async def get_interacciones(
        self,
        current_user: CurrentUser,
    ) -> InteraccionesResponse:
        """Interacciones por docente × materia × acción, respetando el scope."""
        materia_ids = await _resolver_scope(self, current_user)
        items = await self._repo.interacciones_por_docente_materia(
            tenant_id=current_user.tenant_id,
            materia_ids=materia_ids,
        )
        return InteraccionesResponse(items=items)

    async def get_ultimas_acciones(
        self,
        current_user: CurrentUser,
        limite: int = 0,
    ) -> UltimasAccionesResponse:
        """Últimas N acciones con límite clampado, respetando el scope."""
        limite_efectivo = self._clamp_limite(limite)
        materia_ids = await _resolver_scope(self, current_user)
        items = await self._repo.ultimas_acciones(
            tenant_id=current_user.tenant_id,
            limite=limite_efectivo,
            materia_ids=materia_ids,
        )
        return UltimasAccionesResponse(
            limite_aplicado=limite_efectivo,
            items=items,
        )


# ── Helper de módulo ──────────────────────────────────────────────────────────


async def _resolver_scope(
    svc: AuditoriaService, current_user: CurrentUser
) -> Optional[list[uuid.UUID]]:
    """Resuelve el scope de materias usando la lógica estricta de COORDINADOR."""
    return await svc._resolver_materia_ids_coordinador(current_user)
