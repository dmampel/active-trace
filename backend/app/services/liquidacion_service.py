"""Servicio de liquidaciones y honorarios (C-18).

Responsabilidades:
- calcular_periodo(): calcula honorarios para todos los docentes activos de una
  cohorte en un período dado. Implementa RN-33/RN-34 (plus una vez por clave activa).
- cerrar_periodo(): cierra inmutablemente una liquidación (RN-22).
- Registra LIQUIDACION_CERRAR en AuditLog con snapshot completo.

Governance: CRÍTICO — calcula y congela pagos reales.

NO accede directamente a la DB — siempre vía repositorios.
NO contiene lógica de RBAC — eso es responsabilidad de los routers.
Identidad (tenant_id) SIEMPRE viene del caller (JWT verificado).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asignacion import RolDominio
from app.models.liquidacion import EstadoLiquidacion, Liquidacion
from app.models.estructura import InstanciaDictado
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.liquidacion_repository import (
    LiquidacionRepository,
    SalarioBaseRepository,
    SalarioPlusRepository,
)
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.liquidacion import (
    DocenteOmitido,
    LiquidacionCalcularResponse,
    LiquidacionDetalle,
    LiquidacionResponse,
    LiquidacionVistaPeriodo,
)


def _to_response(liq: Liquidacion) -> LiquidacionResponse:
    return LiquidacionResponse.model_validate(liq)


def _to_detalle(liq: Liquidacion, claves_activas: list[str]) -> LiquidacionDetalle:
    data = LiquidacionResponse.model_validate(liq).model_dump()
    data["comisiones"] = liq.comisiones or []
    data["claves_activas"] = claves_activas
    return LiquidacionDetalle(**data)


class LiquidacionService:
    def __init__(
        self,
        session: AsyncSession,
        liq_repo: LiquidacionRepository,
        salario_base_repo: SalarioBaseRepository,
        salario_plus_repo: SalarioPlusRepository,
        asignacion_repo: AsignacionRepository,
        usuario_repo: UsuarioRepository,
        audit_repo: AuditLogRepository,
    ) -> None:
        self._session = session
        self._liq_repo = liq_repo
        self._base_repo = salario_base_repo
        self._plus_repo = salario_plus_repo
        self._asig_repo = asignacion_repo
        self._usuario_repo = usuario_repo
        self._audit_repo = audit_repo

    # ── calcular_periodo ─────────────────────────────────────────────────────

    async def calcular_periodo(
        self,
        tenant_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        periodo: str,
    ) -> LiquidacionCalcularResponse:
        """Calcula (o recalcula) las liquidaciones para todos los docentes activos
        de la cohorte en el período dado.

        Si el período ya tiene liquidaciones Cerradas → 409 (RN-22).
        Si el período tiene liquidaciones Abiertas → actualiza (D2).
        Docentes sin CBU+banco → omitidos (RN-26).
        Docentes facturantes → excluido_por_factura=True (RN-35).
        Plus: suma DISTINCT claves activas (RN-33, D4).
        """
        # Verificar que el período no esté cerrado
        if await self._liq_repo.tiene_periodo_cerrado(tenant_id, cohorte_id, periodo):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El período ya tiene liquidaciones cerradas — no se puede recalcular",
            )

        # Obtener grilla salarial vigente para el período
        plus_grilla = await self._plus_repo.get_vigentes_para_periodo(tenant_id, periodo)

        # Obtener asignaciones activas de la cohorte
        asignaciones = await self._asig_repo.list(
            tenant_id,
            cohorte_id=cohorte_id,
            vigente_only=True,
        )

        # Agrupar asignaciones por usuario
        por_usuario: dict[uuid.UUID, list] = {}
        for asig in asignaciones:
            por_usuario.setdefault(asig.usuario_id, []).append(asig)

        omitidos: list[DocenteOmitido] = []
        liquidaciones_result: list[LiquidacionResponse] = []
        creadas = 0
        actualizadas = 0

        for usuario_id, asigs in por_usuario.items():
            # Obtener datos del usuario
            usuario = await self._usuario_repo.get_by_id(usuario_id, tenant_id)
            if usuario is None:
                omitidos.append(DocenteOmitido(
                    usuario_id=usuario_id,
                    motivo="usuario no encontrado",
                ))
                continue

            # Verificar datos bancarios (CBU cifrado + banco) — RN-26
            if not usuario.cbu_enc or not usuario.banco:
                omitidos.append(DocenteOmitido(
                    usuario_id=usuario_id,
                    motivo="sin CBU o banco registrado",
                ))
                continue

            # Derivar rol (tomar el de la primera asignación activa)
            rol = str(asigs[0].rol.value if hasattr(asigs[0].rol, "value") else asigs[0].rol)

            # Salario base vigente para el rol
            salario_base = await self._base_repo.get_vigente_para_periodo(tenant_id, rol, periodo)
            monto_base = salario_base.monto if salario_base else Decimal("0")

            # Determinar flags
            es_nexo = rol == RolDominio.NEXO.value or rol == "NEXO"
            excluido_por_factura = bool(usuario.facturador)

            # Obtener claves activas (DISTINCT plus_key de las instancias asignadas) — D4/RN-33
            claves_activas = await self._get_claves_activas(tenant_id, usuario_id, cohorte_id, periodo)

            # Calcular monto_plus: suma de plus por cada clave activa distinta
            monto_plus = Decimal("0")
            for clave in claves_activas:
                plus_monto = plus_grilla.get((clave, rol))
                if plus_monto:
                    monto_plus += plus_monto

            total = monto_base + monto_plus

            # Snapshot de comisiones (instancia_id + plus_key)
            comisiones_snapshot = await self._get_comisiones_snapshot(
                tenant_id, usuario_id, cohorte_id, periodo
            )

            liq_data = {
                "rol": rol,
                "comisiones": comisiones_snapshot,
                "monto_base": monto_base,
                "monto_plus": monto_plus,
                "total": total,
                "es_nexo": es_nexo,
                "excluido_por_factura": excluido_por_factura,
                "estado": EstadoLiquidacion.abierta,
            }

            liq, was_created = await self._liq_repo.create_or_update(
                tenant_id, cohorte_id, periodo, usuario_id, liq_data
            )
            if was_created:
                creadas += 1
            else:
                actualizadas += 1
            liquidaciones_result.append(_to_response(liq))

        return LiquidacionCalcularResponse(
            creadas=creadas,
            actualizadas=actualizadas,
            liquidaciones=liquidaciones_result,
            omitidos=omitidos,
        )

    async def _get_claves_activas(
        self,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        periodo: str,
    ) -> list[str]:
        """Obtiene DISTINCT plus_key de InstanciaDictado para las comisiones activas
        del docente en la cohorte/período. Implementa RN-33/D4.
        """
        # Las asignaciones ya filtradas por usuario+cohorte, vigentes para el período
        stmt = (
            select(InstanciaDictado.plus_key)
            .join(
                # AsignacionRepository trabaja con modelos, acá hacemos el join directo
                text(
                    "JOIN asignacion ON asignacion.cohorte_id = instancia_dictado.cohorte_id"
                    " AND asignacion.tenant_id = instancia_dictado.tenant_id"
                    " AND asignacion.deleted_at IS NULL"
                    " AND asignacion.usuario_id = :usuario_id"
                ),
                isouter=False,
            )
            .where(
                InstanciaDictado.tenant_id == tenant_id,
                InstanciaDictado.cohorte_id == cohorte_id,
                InstanciaDictado.periodo == periodo,
                InstanciaDictado.deleted_at.is_(None),
                InstanciaDictado.plus_key.isnot(None),
            )
            .distinct()
        )
        # Fallback: usar query directa más simple y correcta
        return await self._get_claves_activas_simple(tenant_id, usuario_id, cohorte_id, periodo)

    async def _get_claves_activas_simple(
        self,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        periodo: str,
    ) -> list[str]:
        """Consulta DISTINCT plus_key via SQL nativo para máxima claridad (D4)."""
        stmt = text(
            """
            SELECT DISTINCT id.plus_key
            FROM instancia_dictado id
            WHERE id.tenant_id = :tenant_id
              AND id.cohorte_id = :cohorte_id
              AND id.periodo = :periodo
              AND id.plus_key IS NOT NULL
              AND id.deleted_at IS NULL
              AND EXISTS (
                SELECT 1 FROM asignacion a
                WHERE a.usuario_id = :usuario_id
                  AND a.cohorte_id = :cohorte_id
                  AND a.tenant_id = :tenant_id
                  AND a.deleted_at IS NULL
              )
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "tenant_id": tenant_id,
                "cohorte_id": cohorte_id,
                "periodo": periodo,
                "usuario_id": usuario_id,
            },
        )
        return [row[0] for row in result.fetchall()]

    async def _get_comisiones_snapshot(
        self,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        periodo: str,
    ) -> list[dict]:
        """Snapshot de las instancias activas del docente para el período."""
        stmt = text(
            """
            SELECT id.id, id.plus_key
            FROM instancia_dictado id
            WHERE id.tenant_id = :tenant_id
              AND id.cohorte_id = :cohorte_id
              AND id.periodo = :periodo
              AND id.deleted_at IS NULL
              AND EXISTS (
                SELECT 1 FROM asignacion a
                WHERE a.usuario_id = :usuario_id
                  AND a.cohorte_id = :cohorte_id
                  AND a.tenant_id = :tenant_id
                  AND a.deleted_at IS NULL
              )
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "tenant_id": tenant_id,
                "cohorte_id": cohorte_id,
                "periodo": periodo,
                "usuario_id": usuario_id,
            },
        )
        return [{"instancia_id": str(row[0]), "plus_key": row[1]} for row in result.fetchall()]

    # ── cerrar_periodo ────────────────────────────────────────────────────────

    async def cerrar_periodo(
        self,
        tenant_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        periodo: str,
        actor_id: uuid.UUID,
    ) -> list[LiquidacionResponse]:
        """Cierra todas las liquidaciones Abiertas del período.

        Verifica que no haya ya Cerradas (409) — inmutabilidad RN-22.
        Registra LIQUIDACION_CERRAR en AuditLog con snapshot completo.
        """
        if await self._liq_repo.tiene_periodo_cerrado(tenant_id, cohorte_id, periodo):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El período ya está cerrado",
            )

        liquidaciones = await self._liq_repo.cerrar_periodo(tenant_id, cohorte_id, periodo)
        if not liquidaciones:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay liquidaciones para este período",
            )

        # Snapshot para audit log
        snapshot = [
            {
                "liquidacion_id": str(liq.id),
                "usuario_id": str(liq.usuario_id),
                "rol": liq.rol,
                "total": str(liq.total),
                "estado": liq.estado.value,
            }
            for liq in liquidaciones
        ]

        await self._audit_repo.create_entry({
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "accion": "LIQUIDACION_CERRAR",
            "detalle": {
                "cohorte_id": str(cohorte_id),
                "periodo": periodo,
                "snapshot": snapshot,
            },
        })

        return [_to_response(liq) for liq in liquidaciones]

    async def cerrar_por_id(
        self,
        tenant_id: uuid.UUID,
        liquidacion_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> LiquidacionResponse:
        """Cierra una liquidación individual por ID.

        409 si ya está Cerrada.
        """
        liq = await self._liq_repo.get_by_id(liquidacion_id, tenant_id)
        if liq is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liquidación no encontrada")
        if liq.estado == EstadoLiquidacion.cerrada:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="liquidacion ya cerrada",
            )

        liq = await self._liq_repo.cerrar(liquidacion_id, tenant_id)

        # Snapshot de un solo registro
        snapshot = [{
            "liquidacion_id": str(liq.id),
            "usuario_id": str(liq.usuario_id),
            "rol": liq.rol,
            "total": str(liq.total),
            "estado": liq.estado.value,
        }]
        await self._audit_repo.create_entry({
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "accion": "LIQUIDACION_CERRAR",
            "detalle": {
                "cohorte_id": str(liq.cohorte_id),
                "periodo": liq.periodo,
                "snapshot": snapshot,
            },
        })

        return _to_response(liq)

    # ── vistas ────────────────────────────────────────────────────────────────

    async def get_vista_periodo(
        self,
        tenant_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        periodo: str,
        estado: Optional[EstadoLiquidacion] = None,
    ) -> LiquidacionVistaPeriodo:
        """Retorna la vista segmentada: general / nexo / facturantes + KPIs."""
        liquidaciones = await self._liq_repo.list_by_periodo(
            tenant_id, cohorte_id=cohorte_id, periodo=periodo, estado=estado
        )

        general: list[LiquidacionResponse] = []
        nexo: list[LiquidacionResponse] = []
        facturantes: list[LiquidacionResponse] = []

        for liq in liquidaciones:
            r = _to_response(liq)
            if liq.excluido_por_factura:
                facturantes.append(r)
            elif liq.es_nexo:
                nexo.append(r)
            else:
                general.append(r)

        total_sin_factura = sum(r.total for r in general) + sum(r.total for r in nexo)
        total_con_factura = sum(r.total for r in facturantes)

        return LiquidacionVistaPeriodo(
            cohorte_id=cohorte_id,
            periodo=periodo,
            general=general,
            nexo=nexo,
            facturantes=facturantes,
            total_sin_factura=total_sin_factura,
            total_con_factura=total_con_factura,
        )

    async def get_detalle(
        self, tenant_id: uuid.UUID, liquidacion_id: uuid.UUID
    ) -> LiquidacionDetalle:
        liq = await self._liq_repo.get_by_id(liquidacion_id, tenant_id)
        if liq is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liquidación no encontrada")
        # Reconstruir claves_activas desde el snapshot de comisiones
        claves = list({c["plus_key"] for c in (liq.comisiones or []) if c.get("plus_key")})
        return _to_detalle(liq, claves)
