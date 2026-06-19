"""Repositorio de lectura/agregación para el panel de auditoría (C-19).

Responsabilidades:
- Solo lectura sobre AuditLog y Comunicacion (ningún create/update/delete).
- Todas las queries filtran por tenant_id por defecto (row-level isolation).
- Las agregaciones se hacen en DB (func.count, func.date, group_by); no en Python.
- Recibe el scope de materias ya resuelto desde el Service — no decide permisos.
- Soft delete: excluye comunicaciones con deleted_at no nulo.

Separado de AuditLogRepository (append-only de escritura) para mantener la
responsabilidad única y preservar el contrato de inmutabilidad de C-05.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.comunicacion import Comunicacion
from app.schemas.auditoria import (
    AccionPorDiaItem,
    AuditLogEntryResponse,
    EstadoComunicacionesDocenteItem,
    InteraccionDocenteMateriaItem,
    LogCompletoResponse,
)

_DEFAULT_PAGE = 1
_DEFAULT_PAGE_SIZE = 50


class AuditoriaRepository:
    """Repositorio de solo lectura para el panel de auditoría."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── 3.1 list_log ─────────────────────────────────────────────────────────

    async def list_log(
        self,
        tenant_id: uuid.UUID,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        materia_id: Optional[uuid.UUID] = None,
        usuario_id: Optional[uuid.UUID] = None,
        accion: Optional[str] = None,
        materia_ids: Optional[list[uuid.UUID]] = None,
        page: int = _DEFAULT_PAGE,
        page_size: int = _DEFAULT_PAGE_SIZE,
    ) -> LogCompletoResponse:
        """Log completo paginado con filtros opcionales.

        Siempre filtra por tenant_id. Orden descendente por fecha_hora.
        Si se provee `materia_ids` (scope del rol), se restringe a esas materias.
        Si también se provee `materia_id` (filtro explícito del usuario), se aplica
        la intersección — el filtro nunca amplía el scope.
        """
        q = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        # Scope de rol resuelto por el Service
        if materia_ids is not None:
            q = q.where(
                AuditLog.materia_id.in_(materia_ids) if materia_ids else False
            )

        # Filtros opcionales del usuario
        if fecha_desde is not None:
            q = q.where(AuditLog.fecha_hora >= fecha_desde)
        if fecha_hasta is not None:
            q = q.where(AuditLog.fecha_hora <= fecha_hasta)
        if materia_id is not None:
            q = q.where(AuditLog.materia_id == materia_id)
        if usuario_id is not None:
            q = q.where(AuditLog.actor_id == usuario_id)
        if accion is not None:
            q = q.where(AuditLog.accion == accion)

        # Contar total antes de paginar
        count_q = select(func.count()).select_from(q.subquery())
        total_result = await self.session.execute(count_q)
        total = total_result.scalar_one()

        # Paginación
        offset = (page - 1) * page_size
        q = q.order_by(AuditLog.fecha_hora.desc()).offset(offset).limit(page_size)
        rows = await self.session.execute(q)
        items = [_audit_log_to_dto(row) for row in rows.scalars().all()]

        return LogCompletoResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )

    # ── 3.2 acciones_por_dia ─────────────────────────────────────────────────

    async def acciones_por_dia(
        self,
        tenant_id: uuid.UUID,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        materia_ids: Optional[list[uuid.UUID]] = None,
    ) -> list[AccionPorDiaItem]:
        """Cantidad de acciones agrupadas por día.

        Scope: tenant_id obligatorio. materia_ids restringe el scope si se provee.
        """
        # func.date extrae la fecha local; en SQLite usa date(), en PG cast a date
        day_col = func.date(AuditLog.fecha_hora).label("dia")
        q = (
            select(day_col, func.count(AuditLog.id).label("cantidad"))
            .where(AuditLog.tenant_id == tenant_id)
            .group_by(day_col)
            .order_by(day_col)
        )

        if materia_ids is not None:
            if materia_ids:
                q = q.where(AuditLog.materia_id.in_(materia_ids))
            else:
                # scope vacío → sin resultados
                return []

        if fecha_desde is not None:
            q = q.where(AuditLog.fecha_hora >= fecha_desde)
        if fecha_hasta is not None:
            q = q.where(AuditLog.fecha_hora <= fecha_hasta)

        rows = await self.session.execute(q)
        return [
            AccionPorDiaItem(
                fecha=_parse_date(row.dia),
                cantidad=row.cantidad,
            )
            for row in rows.all()
        ]

    # ── 3.3 estado_comunicaciones_por_docente ─────────────────────────────────

    async def estado_comunicaciones_por_docente(
        self,
        tenant_id: uuid.UUID,
        materia_ids: Optional[list[uuid.UUID]] = None,
    ) -> list[EstadoComunicacionesDocenteItem]:
        """Distribución de estados de comunicaciones agrupada por docente y materia.

        Fuente de verdad: tabla `comunicacion` (no AuditLog).
        Scope: tenant_id obligatorio; soft-deleted excluidos.
        """
        q = (
            select(
                Comunicacion.enviado_por,
                Comunicacion.materia_id,
                Comunicacion.estado,
                func.count(Comunicacion.id).label("cantidad"),
            )
            .where(
                Comunicacion.tenant_id == tenant_id,
                Comunicacion.deleted_at.is_(None),
            )
            .group_by(
                Comunicacion.enviado_por,
                Comunicacion.materia_id,
                Comunicacion.estado,
            )
        )

        if materia_ids is not None:
            if materia_ids:
                q = q.where(Comunicacion.materia_id.in_(materia_ids))
            else:
                return []

        rows = await self.session.execute(q)
        return [
            EstadoComunicacionesDocenteItem(
                enviado_por=row.enviado_por,
                materia_id=row.materia_id,
                estado=row.estado.value if hasattr(row.estado, "value") else str(row.estado),
                cantidad=row.cantidad,
            )
            for row in rows.all()
        ]

    # ── 3.4 interacciones_por_docente_materia ─────────────────────────────────

    async def interacciones_por_docente_materia(
        self,
        tenant_id: uuid.UUID,
        materia_ids: Optional[list[uuid.UUID]] = None,
    ) -> list[InteraccionDocenteMateriaItem]:
        """Conteo de acciones de auditoría agrupado por actor, materia y acción.

        Solo incluye registros con materia_id no nulo (acciones con scope de materia).
        Scope: tenant_id obligatorio.
        """
        q = (
            select(
                AuditLog.actor_id,
                AuditLog.materia_id,
                AuditLog.accion,
                func.count(AuditLog.id).label("cantidad"),
            )
            .where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.materia_id.isnot(None),
            )
            .group_by(AuditLog.actor_id, AuditLog.materia_id, AuditLog.accion)
        )

        if materia_ids is not None:
            if materia_ids:
                q = q.where(AuditLog.materia_id.in_(materia_ids))
            else:
                return []

        rows = await self.session.execute(q)
        return [
            InteraccionDocenteMateriaItem(
                actor_id=row.actor_id,
                materia_id=row.materia_id,
                accion=row.accion,
                cantidad=row.cantidad,
            )
            for row in rows.all()
        ]

    # ── 3.5 ultimas_acciones ──────────────────────────────────────────────────

    async def ultimas_acciones(
        self,
        tenant_id: uuid.UUID,
        limite: int,
        materia_ids: Optional[list[uuid.UUID]] = None,
    ) -> list[AuditLogEntryResponse]:
        """Las N acciones más recientes del tenant (o del scope de materias).

        Si `materia_ids` se provee (scope del coordinador), filtra a esas materias
        y excluye registros con materia_id NULL (acciones globales no en su scope).
        ADMIN recibe materia_ids=None → ve todo incluido materia_id NULL.
        """
        q = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.fecha_hora.desc())
            .limit(limite)
        )

        if materia_ids is not None:
            if materia_ids:
                q = (
                    select(AuditLog)
                    .where(
                        AuditLog.tenant_id == tenant_id,
                        AuditLog.materia_id.in_(materia_ids),
                    )
                    .order_by(AuditLog.fecha_hora.desc())
                    .limit(limite)
                )
            else:
                return []

        rows = await self.session.execute(q)
        return [_audit_log_to_dto(row) for row in rows.scalars().all()]


# ── Helpers privados ──────────────────────────────────────────────────────────


def _audit_log_to_dto(entry: AuditLog) -> AuditLogEntryResponse:
    return AuditLogEntryResponse(
        id=entry.id,
        fecha_hora=entry.fecha_hora,
        actor_id=entry.actor_id,
        impersonado_id=entry.impersonado_id,
        materia_id=entry.materia_id,
        accion=entry.accion,
        filas_afectadas=entry.filas_afectadas,
        ip=entry.ip,
        user_agent=entry.user_agent,
    )


def _parse_date(value) -> date:
    """Convierte el resultado de func.date() a un objeto date.

    SQLite devuelve str 'YYYY-MM-DD'; PostgreSQL devuelve date directamente.
    """
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    # fallback: intentar convertir datetime
    if isinstance(value, datetime):
        return value.date()
    raise ValueError(f"No se puede convertir a date: {value!r}")
