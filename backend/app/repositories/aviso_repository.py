"""Repositorio para el módulo de avisos y acknowledgment (C-15).

Todas las queries incluyen filtro tenant_id por defecto — omitirlo es un bug.
Sin lógica de negocio: eso vive en AvisoService.

Métodos clave:
- create / get_by_id / list_all / update / soft_delete
- get_feed: filtra por alcance + vigencia en una sola SQL query (D2)
- upsert_ack: idempotente via ON CONFLICT DO NOTHING (D4)
- count_acks: conteo derivado sin denormalización (D3)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aviso import AcknowledgmentAviso, AlcanceAviso, Aviso


class AvisoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── CRUD básico ───────────────────────────────────────────────────────────

    async def create(self, aviso: Aviso) -> Aviso:
        """Persiste un aviso recién construido."""
        self.session.add(aviso)
        await self.session.flush()
        await self.session.refresh(aviso)
        return aviso

    async def get_by_id(
        self,
        aviso_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[Aviso]:
        """Obtiene un aviso por ID dentro del tenant. None si no existe o soft-deleted."""
        q = select(Aviso).where(
            Aviso.id == aviso_id,
            Aviso.tenant_id == tenant_id,
            Aviso.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_all(self, tenant_id: uuid.UUID) -> list[Aviso]:
        """Lista TODOS los avisos del tenant (activos, inactivos y vencidos).

        Incluye avisos con activo=false y con fin_en en el pasado.
        Excluye solo soft-deleted (deleted_at IS NOT NULL).
        Ordenados por orden ASC.
        """
        q = (
            select(Aviso)
            .where(
                Aviso.tenant_id == tenant_id,
                Aviso.deleted_at.is_(None),
            )
            .order_by(Aviso.orden.asc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def update(
        self,
        aviso_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: dict,
    ) -> Optional[Aviso]:
        """Actualiza campos de un aviso. Retorna None si no existe o soft-deleted."""
        if not data:
            return await self.get_by_id(aviso_id, tenant_id)

        data["updated_at"] = datetime.now(timezone.utc)
        q = (
            update(Aviso)
            .where(
                Aviso.id == aviso_id,
                Aviso.tenant_id == tenant_id,
                Aviso.deleted_at.is_(None),
            )
            .values(**data)
            .returning(Aviso)
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def soft_delete(
        self,
        aviso_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Soft-delete un aviso. Retorna True si existía."""
        q = (
            update(Aviso)
            .where(
                Aviso.id == aviso_id,
                Aviso.tenant_id == tenant_id,
                Aviso.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(q)
        return result.rowcount > 0

    # ── Feed ──────────────────────────────────────────────────────────────────

    async def get_feed(
        self,
        tenant_id: uuid.UUID,
        rol_usuario: str,
        materias_ids: list[uuid.UUID],
        cohortes_ids: list[uuid.UUID],
        usuario_id: uuid.UUID,
    ) -> list[Aviso]:
        """Retorna los avisos del feed del usuario, filtrados en SQL (D2).

        Filtros:
        - tenant_id = :tenant_id
        - activo = true
        - deleted_at IS NULL
        - inicio_en <= NOW() AND (fin_en IS NULL OR fin_en >= NOW())
        - Alcance: Global | PorRol(rol_usuario) | PorMateria(mis_materias) | PorCohorte(mis_cohortes)
        - Si requiere_ack=true, excluye los ya confirmados por usuario_id

        Ordenado por orden ASC, inicio_en DESC.
        """
        now = datetime.now(timezone.utc)

        # Condición de alcance (OR de las 4 variantes)
        alcance_conds = [Aviso.alcance == AlcanceAviso.Global]

        alcance_conds.append(
            and_(
                Aviso.alcance == AlcanceAviso.PorRol,
                Aviso.rol_destino == rol_usuario,
            )
        )

        if materias_ids:
            alcance_conds.append(
                and_(
                    Aviso.alcance == AlcanceAviso.PorMateria,
                    Aviso.materia_id.in_(materias_ids),
                )
            )
        else:
            # Sin materias: avisos PorMateria nunca aplican
            alcance_conds.append(
                and_(
                    Aviso.alcance == AlcanceAviso.PorMateria,
                    Aviso.materia_id.in_([]),  # always-false
                )
            )

        if cohortes_ids:
            alcance_conds.append(
                and_(
                    Aviso.alcance == AlcanceAviso.PorCohorte,
                    Aviso.cohorte_id.in_(cohortes_ids),
                )
            )
        else:
            alcance_conds.append(
                and_(
                    Aviso.alcance == AlcanceAviso.PorCohorte,
                    Aviso.cohorte_id.in_([]),  # always-false
                )
            )

        # Subquery: aviso_ids ya confirmados por este usuario con requiere_ack=true
        # Para excluirlos del feed (D: si requiere_ack=true y ya fue confirmado, no aparece)
        acked_subq = (
            select(AcknowledgmentAviso.aviso_id)
            .where(AcknowledgmentAviso.usuario_id == usuario_id)
            .scalar_subquery()
        )

        q = (
            select(Aviso)
            .where(
                Aviso.tenant_id == tenant_id,
                Aviso.activo.is_(True),
                Aviso.deleted_at.is_(None),
                Aviso.inicio_en <= now,
                or_(Aviso.fin_en.is_(None), Aviso.fin_en >= now),
                or_(*alcance_conds),
                # Excluir avisos con requiere_ack=true que ya fueron confirmados
                or_(
                    Aviso.requiere_ack.is_(False),
                    Aviso.id.not_in(acked_subq),
                ),
            )
            .order_by(Aviso.orden.asc(), Aviso.inicio_en.desc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    # ── Acknowledgment ────────────────────────────────────────────────────────

    async def upsert_ack(
        self,
        aviso_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> AcknowledgmentAviso:
        """Registra confirmación de lectura (idempotente via ON CONFLICT DO NOTHING).

        Si ya existe el par (aviso_id, usuario_id), no falla ni duplica.
        Retorna el registro existente o recién creado.
        """
        now = datetime.now(timezone.utc)
        new_id = uuid.uuid4()

        stmt = pg_insert(AcknowledgmentAviso).values(
            id=new_id,
            aviso_id=aviso_id,
            usuario_id=usuario_id,
            confirmado_at=now,
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uix_ack_aviso_usuario"
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Retornar el registro (sea el nuevo o el preexistente)
        q = select(AcknowledgmentAviso).where(
            AcknowledgmentAviso.aviso_id == aviso_id,
            AcknowledgmentAviso.usuario_id == usuario_id,
        )
        result = await self.session.execute(q)
        return result.scalar_one()

    async def count_acks(self, aviso_id: uuid.UUID) -> int:
        """Cuenta confirmaciones únicas de un aviso (para total_acks / total_vistas)."""
        q = select(func.count()).where(
            AcknowledgmentAviso.aviso_id == aviso_id
        )
        result = await self.session.execute(q)
        return result.scalar_one()

    async def is_acked_by(
        self,
        aviso_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> bool:
        """Verifica si un usuario ya confirmó un aviso."""
        q = select(AcknowledgmentAviso).where(
            AcknowledgmentAviso.aviso_id == aviso_id,
            AcknowledgmentAviso.usuario_id == usuario_id,
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none() is not None
