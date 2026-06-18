"""Repositorios para el módulo de evaluaciones y coloquios (C-14).

Todas las queries incluyen filtro tenant_id por defecto — omitirlo es un bug.
Sin lógica de negocio: eso vive en EvaluacionService.

Contiene:
- EvaluacionRepository: CRUD + métricas + reserva atómica + resultados
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluacion import (
    EstadoReserva,
    Evaluacion,
    EvaluacionAlumno,
    ReservaEvaluacion,
    ResultadoEvaluacion,
)
from app.schemas.evaluacion import (
    AgendaEntradaRead,
    MetricasColoquioRead,
    ReservaEvaluacionRead,
    ResultadoEvaluacionRead,
)


class ConflictError(Exception):
    """Cupo agotado o conflicto de reserva."""


class EvaluacionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── CRUD básico ───────────────────────────────────────────────────────────

    async def create(self, evaluacion: Evaluacion) -> Evaluacion:
        """Persiste una evaluación recién construida."""
        self.session.add(evaluacion)
        await self.session.flush()
        await self.session.refresh(evaluacion)
        return evaluacion

    async def get_by_id(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[Evaluacion]:
        """Obtiene una evaluación por ID dentro del tenant."""
        conditions = [
            Evaluacion.id == evaluacion_id,
            Evaluacion.tenant_id == tenant_id,
        ]
        if not include_deleted:
            conditions.append(Evaluacion.deleted_at.is_(None))
        q = select(Evaluacion).where(and_(*conditions))
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Evaluacion]:
        """Lista evaluaciones activas del tenant (excluye soft deleted)."""
        q = (
            select(Evaluacion)
            .where(
                Evaluacion.tenant_id == tenant_id,
                Evaluacion.deleted_at.is_(None),
            )
            .order_by(Evaluacion.created_at.desc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def update(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        instancia: Optional[str] = None,
        cupos_por_dia: Optional[dict] = None,
        tipo=None,
    ) -> Optional[Evaluacion]:
        """Actualiza campos de una evaluación. Retorna None si no existe."""
        values: dict = {"updated_at": datetime.now(timezone.utc)}
        if instancia is not None:
            values["instancia"] = instancia
        if cupos_por_dia is not None:
            values["cupos_por_dia"] = cupos_por_dia
        if tipo is not None:
            values["tipo"] = tipo

        q = (
            update(Evaluacion)
            .where(
                Evaluacion.id == evaluacion_id,
                Evaluacion.tenant_id == tenant_id,
                Evaluacion.deleted_at.is_(None),
            )
            .values(**values)
            .returning(Evaluacion)
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def soft_delete(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Soft-delete una evaluación. Retorna True si existía."""
        q = (
            update(Evaluacion)
            .where(
                Evaluacion.id == evaluacion_id,
                Evaluacion.tenant_id == tenant_id,
                Evaluacion.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(q)
        return result.rowcount > 0

    # ── Alumnos habilitados ───────────────────────────────────────────────────

    async def import_alumnos(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
        alumno_ids: list[uuid.UUID],
    ) -> int:
        """Upsert masivo de alumnos habilitados. Retorna total convocados."""
        if not alumno_ids:
            return await self._count_convocados(evaluacion_id, tenant_id)

        rows = [
            {
                "evaluacion_id": evaluacion_id,
                "alumno_id": aid,
                "tenant_id": tenant_id,
            }
            for aid in alumno_ids
        ]
        stmt = pg_insert(EvaluacionAlumno).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["evaluacion_id", "alumno_id"]
        )
        await self.session.execute(stmt)
        return await self._count_convocados(evaluacion_id, tenant_id)

    async def _count_convocados(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> int:
        q = select(func.count()).where(
            EvaluacionAlumno.evaluacion_id == evaluacion_id,
            EvaluacionAlumno.tenant_id == tenant_id,
        )
        result = await self.session.execute(q)
        return result.scalar_one()

    async def is_alumno_habilitado(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Verifica si el alumno está en la lista de convocados."""
        q = select(EvaluacionAlumno).where(
            EvaluacionAlumno.evaluacion_id == evaluacion_id,
            EvaluacionAlumno.alumno_id == alumno_id,
            EvaluacionAlumno.tenant_id == tenant_id,
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none() is not None

    async def get_reserva_activa(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[ReservaEvaluacion]:
        """Obtiene la reserva activa de un alumno en una evaluación."""
        q = select(ReservaEvaluacion).where(
            ReservaEvaluacion.evaluacion_id == evaluacion_id,
            ReservaEvaluacion.alumno_id == alumno_id,
            ReservaEvaluacion.tenant_id == tenant_id,
            ReservaEvaluacion.estado == EstadoReserva.Activa,
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    # ── Reserva atómica ───────────────────────────────────────────────────────

    async def reservar_turno(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
        tenant_id: uuid.UUID,
        fecha: str,
    ) -> ReservaEvaluacion:
        """Reserva un turno decrementando el cupo atómicamente (D1).

        Usa UPDATE ... WHERE (cupos_por_dia->>:fecha)::int > 0 RETURNING id.
        Si no retorna filas → raise ConflictError (cupo agotado).
        """
        # UPDATE atómico con jsonb_set para decrementar cupo
        atomic_q = text(
            """
            UPDATE evaluacion
            SET cupos_por_dia = jsonb_set(
                cupos_por_dia,
                ARRAY[:fecha],
                ((cupos_por_dia->>:fecha)::int - 1)::text::jsonb
            ),
            updated_at = now()
            WHERE id = :evaluacion_id
              AND tenant_id = :tenant_id
              AND deleted_at IS NULL
              AND (cupos_por_dia->>:fecha) IS NOT NULL
              AND (cupos_por_dia->>:fecha)::int > 0
            RETURNING id
            """
        )
        result = await self.session.execute(
            atomic_q,
            {
                "fecha": fecha,
                "evaluacion_id": evaluacion_id,
                "tenant_id": tenant_id,
            },
        )
        row = result.fetchone()
        if row is None:
            raise ConflictError("Cupo agotado para la fecha seleccionada")

        reserva = ReservaEvaluacion(
            tenant_id=tenant_id,
            evaluacion_id=evaluacion_id,
            alumno_id=alumno_id,
            fecha=fecha,
            estado=EstadoReserva.Activa,
        )
        self.session.add(reserva)
        await self.session.flush()
        await self.session.refresh(reserva)
        return reserva

    async def cancelar_reserva(
        self,
        reserva_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Cancela una reserva y restaura el cupo en JSONB. Retorna True si existía."""
        # Obtener la reserva primero para conocer la fecha
        q = select(ReservaEvaluacion).where(
            ReservaEvaluacion.id == reserva_id,
            ReservaEvaluacion.tenant_id == tenant_id,
            ReservaEvaluacion.estado == EstadoReserva.Activa,
        )
        result = await self.session.execute(q)
        reserva = result.scalar_one_or_none()
        if reserva is None:
            return False

        fecha = reserva.fecha
        evaluacion_id = reserva.evaluacion_id

        # Marcar cancelada
        await self.session.execute(
            update(ReservaEvaluacion)
            .where(ReservaEvaluacion.id == reserva_id)
            .values(estado=EstadoReserva.Cancelada, updated_at=datetime.now(timezone.utc))
        )

        # Restaurar cupo atómicamente
        restore_q = text(
            """
            UPDATE evaluacion
            SET cupos_por_dia = jsonb_set(
                cupos_por_dia,
                ARRAY[:fecha],
                ((cupos_por_dia->>:fecha)::int + 1)::text::jsonb
            ),
            updated_at = now()
            WHERE id = :evaluacion_id
              AND tenant_id = :tenant_id
              AND (cupos_por_dia->>:fecha) IS NOT NULL
            """
        )
        await self.session.execute(
            restore_q,
            {
                "fecha": fecha,
                "evaluacion_id": evaluacion_id,
                "tenant_id": tenant_id,
            },
        )
        return True

    # ── Métricas ──────────────────────────────────────────────────────────────

    async def get_metricas(self, tenant_id: uuid.UUID) -> MetricasColoquioRead:
        """Calcula métricas del módulo de coloquios para el tenant."""
        # Total convocados
        q_convocados = select(func.count()).where(
            EvaluacionAlumno.tenant_id == tenant_id
        )
        total_convocados = (await self.session.execute(q_convocados)).scalar_one()

        # Instancias activas (no soft-deleted)
        q_activas = select(func.count()).where(
            Evaluacion.tenant_id == tenant_id,
            Evaluacion.deleted_at.is_(None),
        )
        instancias_activas = (await self.session.execute(q_activas)).scalar_one()

        # Reservas activas
        q_reservas = select(func.count()).where(
            ReservaEvaluacion.tenant_id == tenant_id,
            ReservaEvaluacion.estado == EstadoReserva.Activa,
        )
        reservas_activas = (await self.session.execute(q_reservas)).scalar_one()

        # Notas registradas
        q_notas = select(func.count()).where(
            ResultadoEvaluacion.tenant_id == tenant_id,
        )
        notas_registradas = (await self.session.execute(q_notas)).scalar_one()

        return MetricasColoquioRead(
            total_convocados=total_convocados,
            instancias_activas=instancias_activas,
            reservas_activas=reservas_activas,
            notas_registradas=notas_registradas,
        )

    # ── Agenda ────────────────────────────────────────────────────────────────

    async def get_agenda(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[AgendaEntradaRead]:
        """Lista reservas activas de una evaluación, ordenadas por fecha."""
        q = (
            select(ReservaEvaluacion)
            .where(
                ReservaEvaluacion.evaluacion_id == evaluacion_id,
                ReservaEvaluacion.tenant_id == tenant_id,
                ReservaEvaluacion.estado == EstadoReserva.Activa,
            )
            .order_by(ReservaEvaluacion.fecha.asc())
        )
        result = await self.session.execute(q)
        reservas = result.scalars().all()
        return [
            AgendaEntradaRead(
                reserva_id=r.id,
                alumno_id=r.alumno_id,
                fecha=r.fecha,
                estado=r.estado,
            )
            for r in reservas
        ]

    # ── Resultados ────────────────────────────────────────────────────────────

    async def get_resultados(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[ResultadoEvaluacionRead]:
        """Lista resultados de una evaluación (incluso si la evaluación está soft-deleted)."""
        q = (
            select(ResultadoEvaluacion)
            .where(
                ResultadoEvaluacion.evaluacion_id == evaluacion_id,
                ResultadoEvaluacion.tenant_id == tenant_id,
            )
            .order_by(ResultadoEvaluacion.created_at.asc())
        )
        result = await self.session.execute(q)
        rows = result.scalars().all()
        return [
            ResultadoEvaluacionRead(
                id=r.id,
                evaluacion_id=r.evaluacion_id,
                alumno_id=r.alumno_id,
                nota_final=r.nota_final,
            )
            for r in rows
        ]

    async def upsert_resultado(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
        tenant_id: uuid.UUID,
        nota_final: str,
    ) -> ResultadoEvaluacion:
        """Crea o actualiza el resultado de un alumno en una evaluación."""
        now = datetime.now(timezone.utc)
        result_id = uuid.uuid4()

        stmt = pg_insert(ResultadoEvaluacion).values(
            id=result_id,
            evaluacion_id=evaluacion_id,
            alumno_id=alumno_id,
            tenant_id=tenant_id,
            nota_final=nota_final,
            created_at=now,
            updated_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_resultado_evaluacion_alumno",
            set_={"nota_final": nota_final, "updated_at": now},
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Retornar el registro upsertado
        q = select(ResultadoEvaluacion).where(
            ResultadoEvaluacion.evaluacion_id == evaluacion_id,
            ResultadoEvaluacion.alumno_id == alumno_id,
            ResultadoEvaluacion.tenant_id == tenant_id,
        )
        row = await self.session.execute(q)
        return row.scalar_one()
