"""Repositorios para el módulo de liquidaciones y honorarios (C-18).

Reglas:
- Toda query filtra por tenant_id por defecto (row-level isolation).
- Soft delete via deleted_at — nunca hard delete.
- No lógica de negocio: eso pertenece al Service.
- Liquidacion cerrada: el Service valida el estado antes de llamar a estos métodos.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.liquidacion import (
    EstadoFactura,
    EstadoLiquidacion,
    Factura,
    Liquidacion,
    SalarioBase,
    SalarioPlus,
)


# ────────────────────────────────────────────────────────────────────────────────
# SalarioBaseRepository
# ────────────────────────────────────────────────────────────────────────────────


class SalarioBaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, data: dict) -> SalarioBase:
        obj = SalarioBase(id=uuid.uuid4(), tenant_id=tenant_id, **data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[SalarioBase]:
        q = select(SalarioBase).where(
            SalarioBase.tenant_id == tenant_id,
            SalarioBase.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, obj_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[SalarioBase]:
        q = select(SalarioBase).where(
            SalarioBase.id == obj_id,
            SalarioBase.tenant_id == tenant_id,
            SalarioBase.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def update(self, obj_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> Optional[SalarioBase]:
        obj = await self.get_by_id(obj_id, tenant_id)
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_vigente_para_periodo(
        self, tenant_id: uuid.UUID, rol: str, periodo: str
    ) -> Optional[SalarioBase]:
        """Retorna el SalarioBase vigente cuya vigencia contiene el período dado.

        Un período "YYYY-MM" se interpreta como el rango completo del mes.
        La lógica: desde <= fin_mes AND (hasta IS NULL OR hasta >= inicio_mes).
        """
        try:
            year, month = int(periodo[:4]), int(periodo[5:7])
        except (ValueError, IndexError):
            return None

        # Calcular inicio y fin del mes
        inicio_mes = date(year, month, 1)
        # Último día del mes
        if month == 12:
            fin_mes = date(year + 1, 1, 1).replace(day=1)
            import calendar
            fin_mes = date(year, month, calendar.monthrange(year, month)[1])
        else:
            import calendar
            fin_mes = date(year, month, calendar.monthrange(year, month)[1])

        q = select(SalarioBase).where(
            SalarioBase.tenant_id == tenant_id,
            SalarioBase.rol == rol,
            SalarioBase.deleted_at.is_(None),
            SalarioBase.desde <= fin_mes,
            or_(SalarioBase.hasta.is_(None), SalarioBase.hasta >= inicio_mes),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def check_solapamiento(
        self,
        tenant_id: uuid.UUID,
        rol: str,
        desde: date,
        hasta: Optional[date],
        exclude_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Retorna True si existe solapamiento de vigencia para el rol dado.

        Solapamiento: el rango nuevo [desde, hasta] intersecta con algún registro existente.
        Un rango abierto (hasta=None) solapa con cualquier fecha futura.
        """
        conditions = [
            SalarioBase.tenant_id == tenant_id,
            SalarioBase.rol == rol,
            SalarioBase.deleted_at.is_(None),
        ]
        if exclude_id:
            conditions.append(SalarioBase.id != exclude_id)

        # Condición de solapamiento:
        # nuevo_desde <= existente_hasta AND (nuevo_hasta IS NULL OR nuevo_hasta >= existente_desde)
        if hasta is not None:
            conditions.append(SalarioBase.desde <= hasta)
        # Si hasta is None → el nuevo es abierto → siempre solapa con cualquier registro que
        # empiece antes o no tenga hasta
        conditions.append(
            or_(SalarioBase.hasta.is_(None), SalarioBase.hasta >= desde)
        )

        q = select(func.count()).where(*conditions)
        result = await self.session.execute(q)
        count = result.scalar_one()
        return count > 0


# ────────────────────────────────────────────────────────────────────────────────
# SalarioPlusRepository
# ────────────────────────────────────────────────────────────────────────────────


class SalarioPlusRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, data: dict) -> SalarioPlus:
        obj = SalarioPlus(id=uuid.uuid4(), tenant_id=tenant_id, **data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[SalarioPlus]:
        q = select(SalarioPlus).where(
            SalarioPlus.tenant_id == tenant_id,
            SalarioPlus.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, obj_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[SalarioPlus]:
        q = select(SalarioPlus).where(
            SalarioPlus.id == obj_id,
            SalarioPlus.tenant_id == tenant_id,
            SalarioPlus.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def update(self, obj_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> Optional[SalarioPlus]:
        obj = await self.get_by_id(obj_id, tenant_id)
        if not obj:
            return None
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_vigentes_para_periodo(
        self, tenant_id: uuid.UUID, periodo: str
    ) -> dict[tuple[str, str], Decimal]:
        """Retorna dict {(grupo, rol): monto} de plus vigentes para el período.

        Implementa D4: la clave es (grupo, rol) para el lookup por docente.
        """
        try:
            year, month = int(periodo[:4]), int(periodo[5:7])
        except (ValueError, IndexError):
            return {}

        import calendar
        inicio_mes = date(year, month, 1)
        fin_mes = date(year, month, calendar.monthrange(year, month)[1])

        q = select(SalarioPlus).where(
            SalarioPlus.tenant_id == tenant_id,
            SalarioPlus.deleted_at.is_(None),
            SalarioPlus.desde <= fin_mes,
            or_(SalarioPlus.hasta.is_(None), SalarioPlus.hasta >= inicio_mes),
        )
        result = await self.session.execute(q)
        rows = result.scalars().all()
        return {(r.grupo, r.rol): r.monto for r in rows}


# ────────────────────────────────────────────────────────────────────────────────
# LiquidacionRepository
# ────────────────────────────────────────────────────────────────────────────────


class LiquidacionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update(
        self, tenant_id: uuid.UUID, cohorte_id: uuid.UUID, periodo: str, usuario_id: uuid.UUID, data: dict
    ) -> tuple[Liquidacion, bool]:
        """Crea o actualiza la liquidación para (cohorte, período, usuario).

        Retorna (liquidacion, creada: bool).
        No verifica inmutabilidad — eso es responsabilidad del Service.
        """
        q = select(Liquidacion).where(
            Liquidacion.tenant_id == tenant_id,
            Liquidacion.cohorte_id == cohorte_id,
            Liquidacion.periodo == periodo,
            Liquidacion.usuario_id == usuario_id,
            Liquidacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        existing = result.scalar_one_or_none()

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            existing.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing, False
        else:
            obj = Liquidacion(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cohorte_id=cohorte_id,
                periodo=periodo,
                usuario_id=usuario_id,
                **data,
            )
            self.session.add(obj)
            await self.session.flush()
            await self.session.refresh(obj)
            return obj, True

    async def list_by_periodo(
        self,
        tenant_id: uuid.UUID,
        cohorte_id: Optional[uuid.UUID] = None,
        periodo: Optional[str] = None,
        estado: Optional[EstadoLiquidacion] = None,
    ) -> list[Liquidacion]:
        conditions = [
            Liquidacion.tenant_id == tenant_id,
            Liquidacion.deleted_at.is_(None),
        ]
        if cohorte_id:
            conditions.append(Liquidacion.cohorte_id == cohorte_id)
        if periodo:
            conditions.append(Liquidacion.periodo == periodo)
        if estado:
            conditions.append(Liquidacion.estado == estado)

        q = select(Liquidacion).where(*conditions)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, obj_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Liquidacion]:
        q = select(Liquidacion).where(
            Liquidacion.id == obj_id,
            Liquidacion.tenant_id == tenant_id,
            Liquidacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def cerrar(self, obj_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Liquidacion]:
        """Cambia estado de Abierta → Cerrada. No valida el estado previo (lo hace el Service)."""
        obj = await self.get_by_id(obj_id, tenant_id)
        if not obj:
            return None
        obj.estado = EstadoLiquidacion.cerrada
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def cerrar_periodo(
        self, tenant_id: uuid.UUID, cohorte_id: uuid.UUID, periodo: str
    ) -> list[Liquidacion]:
        """Cierra todas las liquidaciones Abiertas de un período. Retorna las cerradas."""
        liquidaciones = await self.list_by_periodo(
            tenant_id, cohorte_id=cohorte_id, periodo=periodo
        )
        closed = []
        for liq in liquidaciones:
            if liq.estado == EstadoLiquidacion.abierta:
                liq.estado = EstadoLiquidacion.cerrada
                liq.updated_at = datetime.now(timezone.utc)
                closed.append(liq)
        if closed:
            await self.session.flush()
        return liquidaciones  # todas, no solo las que se cerraron

    async def list_historial(
        self, tenant_id: uuid.UUID, cohorte_id: uuid.UUID
    ) -> list[Liquidacion]:
        """Historial de liquidaciones Cerradas ordenado por período descendente."""
        q = (
            select(Liquidacion)
            .where(
                Liquidacion.tenant_id == tenant_id,
                Liquidacion.cohorte_id == cohorte_id,
                Liquidacion.estado == EstadoLiquidacion.cerrada,
                Liquidacion.deleted_at.is_(None),
            )
            .order_by(Liquidacion.periodo.desc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def tiene_periodo_cerrado(
        self, tenant_id: uuid.UUID, cohorte_id: uuid.UUID, periodo: str
    ) -> bool:
        """Retorna True si existe al menos una liquidación Cerrada para el período."""
        q = select(func.count()).where(
            Liquidacion.tenant_id == tenant_id,
            Liquidacion.cohorte_id == cohorte_id,
            Liquidacion.periodo == periodo,
            Liquidacion.estado == EstadoLiquidacion.cerrada,
            Liquidacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one() > 0


# ────────────────────────────────────────────────────────────────────────────────
# FacturaRepository
# ────────────────────────────────────────────────────────────────────────────────


class FacturaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Factura:
        obj = Factura(id=uuid.uuid4(), tenant_id=tenant_id, **data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, obj_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Factura]:
        q = select(Factura).where(
            Factura.id == obj_id,
            Factura.tenant_id == tenant_id,
            Factura.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
        estado: Optional[EstadoFactura] = None,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
    ) -> list[Factura]:
        conditions = [
            Factura.tenant_id == tenant_id,
            Factura.deleted_at.is_(None),
        ]
        if usuario_id:
            conditions.append(Factura.usuario_id == usuario_id)
        if estado:
            conditions.append(Factura.estado == estado)
        if desde:
            conditions.append(Factura.periodo >= desde)
        if hasta:
            conditions.append(Factura.periodo <= hasta)

        q = select(Factura).where(*conditions).order_by(Factura.periodo.desc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def update_estado(
        self, obj_id: uuid.UUID, tenant_id: uuid.UUID, estado: EstadoFactura
    ) -> Optional[Factura]:
        obj = await self.get_by_id(obj_id, tenant_id)
        if not obj:
            return None
        obj.estado = estado
        if estado == EstadoFactura.abonada:
            obj.abonada_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
