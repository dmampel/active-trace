"""Repositorio de asignaciones contextuales.

Reglas:
- Toda query filtra por tenant_id por defecto (row-level isolation).
- Soft delete via deleted_at — nunca hard delete.
- estado_vigencia NO se almacena — se deriva en derive_estado_vigencia().
- No lógica de negocio: eso pertenece al Service.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asignacion import Asignacion
from app.models.estructura import Carrera, Cohorte, Materia
from app.models.user import User


class AsignacionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def derive_estado_vigencia(asig: Asignacion) -> str:
        """Deriva el estado de vigencia de una asignación.

        Vigente: desde <= hoy AND (hasta IS NULL OR hoy <= hasta)
        Vencida: hasta < hoy
        """
        today = date.today()
        if asig.desde > today:
            return "Futura"
        if asig.hasta is not None and asig.hasta < today:
            return "Vencida"
        return "Vigente"

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Asignacion:
        asig = Asignacion(id=uuid.uuid4(), tenant_id=tenant_id, **data)
        self.session.add(asig)
        await self.session.commit()
        await self.session.refresh(asig)
        return asig

    async def get_by_id(self, asig_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Asignacion]:
        q = select(Asignacion).where(
            Asignacion.id == asig_id,
            Asignacion.tenant_id == tenant_id,
            Asignacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_vigentes(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> list[Asignacion]:
        """Alias conveniente: asignaciones vigentes de un tenant (opcionalmente por usuario)."""
        return await self.list(
            tenant_id,
            usuario_id=user_id,
            vigente_only=True,
        )

    async def update(
        self, asig_id: uuid.UUID, tenant_id: uuid.UUID, data: dict
    ) -> Optional[Asignacion]:
        asig = await self.get_by_id(asig_id, tenant_id)
        if not asig:
            return None
        for k, v in data.items():
            setattr(asig, k, v)
        await self.session.commit()
        await self.session.refresh(asig)
        return asig

    async def soft_delete(self, asig_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        asig = await self.get_by_id(asig_id, tenant_id)
        if not asig:
            return False
        asig.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    # ── Métodos C-08: operaciones colectivas sobre equipos ────────────────────

    async def list(
        self,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        carrera_id: Optional[uuid.UUID] = None,
        rol: Optional[str] = None,
        vigente_only: bool = False,
    ) -> list[Asignacion]:
        """Lista asignaciones con filtros opcionales, siempre acotadas a tenant.

        Extiende el método original con filtros adicionales: carrera_id.
        """
        conditions = [
            Asignacion.tenant_id == tenant_id,
            Asignacion.deleted_at.is_(None),
        ]
        if usuario_id is not None:
            conditions.append(Asignacion.usuario_id == usuario_id)
        if materia_id is not None:
            conditions.append(Asignacion.materia_id == materia_id)
        if cohorte_id is not None:
            conditions.append(Asignacion.cohorte_id == cohorte_id)
        if carrera_id is not None:
            conditions.append(Asignacion.carrera_id == carrera_id)
        if rol is not None:
            conditions.append(Asignacion.rol == rol)
        if vigente_only:
            today = date.today()
            conditions.append(Asignacion.desde <= today)
            conditions.append(or_(Asignacion.hasta.is_(None), Asignacion.hasta >= today))

        q = select(Asignacion).where(*conditions)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def list_for_usuario(
        self,
        usuario_id: uuid.UUID,
        tenant_id: uuid.UUID,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        carrera_id: Optional[uuid.UUID] = None,
        rol: Optional[str] = None,
    ) -> list[Asignacion]:
        """Lista asignaciones del usuario autenticado con filtros opcionales.

        Siempre fija usuario_id — para el endpoint mis-asignaciones.
        """
        return await self.list(
            tenant_id,
            usuario_id=usuario_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            carrera_id=carrera_id,
            rol=rol,
        )

    async def bulk_create(self, tenant_id: uuid.UUID, items: list[dict]) -> int:
        """Inserta múltiples asignaciones en un solo statement.

        Retorna el count de filas insertadas.
        """
        if not items:
            return 0
        now = datetime.now(timezone.utc)
        rows = [
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "created_at": now,
                "updated_at": now,
                **item,
            }
            for item in items
        ]
        await self.session.execute(insert(Asignacion).values(rows))
        await self.session.commit()
        return len(rows)

    async def clone(
        self,
        tenant_id: uuid.UUID,
        origen: dict,
        destino: dict,
    ) -> tuple[int, int]:
        """Clona asignaciones vigentes de un equipo origen a un destino distinto.

        Solo se clonan asignaciones no eliminadas con hasta IS NULL o hasta >= hoy.
        Asignaciones que ya existen en destino (mismo usuario+rol+materia+carrera+cohorte)
        se omiten silenciosamente.

        Retorna (clonadas, omitidas).
        """
        today = date.today()

        # 1. Leer vigentes del origen
        conditions_origen = [
            Asignacion.tenant_id == tenant_id,
            Asignacion.deleted_at.is_(None),
            Asignacion.cohorte_id == origen.get("cohorte_id"),
            or_(Asignacion.hasta.is_(None), Asignacion.hasta >= today),
        ]
        if origen.get("materia_id"):
            conditions_origen.append(Asignacion.materia_id == origen["materia_id"])
        if origen.get("carrera_id"):
            conditions_origen.append(Asignacion.carrera_id == origen["carrera_id"])

        result_origen = await self.session.execute(
            select(Asignacion).where(*conditions_origen)
        )
        vigentes = list(result_origen.scalars().all())

        if not vigentes:
            return 0, 0

        # 2. Leer asignaciones ya existentes en destino para detectar duplicados
        conditions_destino = [
            Asignacion.tenant_id == tenant_id,
            Asignacion.deleted_at.is_(None),
            Asignacion.cohorte_id == destino.get("cohorte_id"),
        ]
        if destino.get("materia_id"):
            conditions_destino.append(Asignacion.materia_id == destino["materia_id"])
        if destino.get("carrera_id"):
            conditions_destino.append(Asignacion.carrera_id == destino["carrera_id"])

        result_destino = await self.session.execute(
            select(Asignacion).where(*conditions_destino)
        )
        existentes = list(result_destino.scalars().all())

        # Conjunto de (usuario_id, rol) ya presentes en destino
        existentes_key = {
            (str(e.usuario_id), str(e.rol)) for e in existentes
        }

        # 3. Filtrar y construir nuevas filas
        now = datetime.now(timezone.utc)
        nuevas = []
        omitidas = 0
        for asig in vigentes:
            key = (str(asig.usuario_id), str(asig.rol))
            if key in existentes_key:
                omitidas += 1
                continue
            nuevas.append({
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "usuario_id": asig.usuario_id,
                "rol": asig.rol,
                "materia_id": destino.get("materia_id"),
                "carrera_id": destino.get("carrera_id"),
                "cohorte_id": destino["cohorte_id"],
                "comisiones": [],
                "responsable_id": asig.responsable_id,
                "desde": asig.desde,
                "hasta": asig.hasta,
                "created_at": now,
                "updated_at": now,
            })

        if nuevas:
            await self.session.execute(insert(Asignacion).values(nuevas))
            await self.session.commit()

        return len(nuevas), omitidas

    async def bulk_update_vigencia(
        self,
        tenant_id: uuid.UUID,
        filtro: dict,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
    ) -> int:
        """Actualiza desde/hasta de todas las asignaciones de un equipo.

        Retorna el count de filas actualizadas.
        """
        conditions = [
            Asignacion.tenant_id == tenant_id,
            Asignacion.deleted_at.is_(None),
            Asignacion.cohorte_id == filtro["cohorte_id"],
        ]
        if filtro.get("materia_id"):
            conditions.append(Asignacion.materia_id == filtro["materia_id"])
        if filtro.get("carrera_id"):
            conditions.append(Asignacion.carrera_id == filtro["carrera_id"])

        values: dict = {"updated_at": datetime.now(timezone.utc)}
        if desde is not None:
            values["desde"] = desde
        if hasta is not None:
            values["hasta"] = hasta

        stmt = (
            update(Asignacion)
            .where(and_(*conditions))
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def export_query(self, tenant_id: uuid.UUID):
        """Retorna rows con join a User, Materia, Carrera, Cohorte para CSV export.

        Yields tuples: (nombre, apellidos, legajo, rol, materia_nombre,
                        carrera_nombre, cohorte_nombre, desde, hasta)
        """
        stmt = (
            select(
                User.nombre,
                User.apellidos,
                User.legajo,
                Asignacion.rol,
                Materia.nombre.label("materia_nombre"),
                Carrera.nombre.label("carrera_nombre"),
                Cohorte.nombre.label("cohorte_nombre"),
                Asignacion.desde,
                Asignacion.hasta,
            )
            .join(User, User.id == Asignacion.usuario_id)
            .outerjoin(Materia, Materia.id == Asignacion.materia_id)
            .outerjoin(Carrera, Carrera.id == Asignacion.carrera_id)
            .outerjoin(Cohorte, Cohorte.id == Asignacion.cohorte_id)
            .where(
                Asignacion.tenant_id == tenant_id,
                Asignacion.deleted_at.is_(None),
            )
            .order_by(User.apellidos, User.nombre)
        )
        result = await self.session.execute(stmt)
        return result.all()
