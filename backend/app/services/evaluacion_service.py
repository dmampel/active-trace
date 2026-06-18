"""Servicio para el módulo de evaluaciones y coloquios (C-14).

Responsabilidades:
- Orquestar CRUD de Evaluacion delegando a EvaluacionRepository.
- importar_alumnos(): valida que los alumno_ids sean del tenant antes de importar.
- reservar_turno(): valida habilitación y reserva duplicada, luego reserva atómica.
- cancelar_reserva(): valida que la reserva pertenece al alumno, luego cancela.
- get_metricas(): delega a repository.
- upsert_resultado(): valida tenant, delega a repository.

NO accede directamente a la DB — siempre vía repositorios.
NO contiene lógica de RBAC — eso es responsabilidad de los routers.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status

from app.models.evaluacion import Evaluacion
from app.repositories.evaluacion_repository import ConflictError, EvaluacionRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.evaluacion import (
    AgendaEntradaRead,
    EvaluacionAlumnoImportResult,
    EvaluacionCreate,
    EvaluacionRead,
    EvaluacionUpdate,
    MetricasColoquioRead,
    ReservaEvaluacionRead,
    ResultadoEvaluacionRead,
    ResultadoEvaluacionUpsert,
)


class EvaluacionService:
    def __init__(
        self,
        evaluacion_repo: EvaluacionRepository,
        usuario_repo: UsuarioRepository,
    ) -> None:
        self.repo = evaluacion_repo
        self.usuario_repo = usuario_repo

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def crear(
        self,
        data: EvaluacionCreate,
        tenant_id: uuid.UUID,
    ) -> EvaluacionRead:
        """Crea una convocatoria de evaluación."""
        ev = Evaluacion(
            tenant_id=tenant_id,
            materia_id=data.materia_id,
            cohorte_id=data.cohorte_id,
            tipo=data.tipo,
            instancia=data.instancia,
            cupos_por_dia=data.cupos_por_dia,
        )
        ev = await self.repo.create(ev)
        return _to_read(ev)

    async def listar(self, tenant_id: uuid.UUID) -> list[EvaluacionRead]:
        """Lista convocatorias activas del tenant."""
        items = await self.repo.list_by_tenant(tenant_id)
        return [_to_read(e) for e in items]

    async def obtener(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> EvaluacionRead:
        """Obtiene una convocatoria por ID. Retorna 404 si no existe."""
        ev = await self.repo.get_by_id(evaluacion_id, tenant_id)
        if ev is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Convocatoria no encontrada",
            )
        return _to_read(ev)

    async def actualizar(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: EvaluacionUpdate,
    ) -> EvaluacionRead:
        """Actualiza campos de una convocatoria."""
        ev = await self.repo.update(
            evaluacion_id,
            tenant_id,
            instancia=data.instancia,
            cupos_por_dia=data.cupos_por_dia,
            tipo=data.tipo,
        )
        if ev is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Convocatoria no encontrada",
            )
        return _to_read(ev)

    async def eliminar(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        """Soft-delete una convocatoria."""
        deleted = await self.repo.soft_delete(evaluacion_id, tenant_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Convocatoria no encontrada",
            )

    # ── Alumnos habilitados ───────────────────────────────────────────────────

    async def importar_alumnos(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
        alumno_ids: list[uuid.UUID],
    ) -> EvaluacionAlumnoImportResult:
        """Importa alumnos habilitados a una convocatoria.

        Valida que todos los alumno_ids pertenezcan al tenant.
        Los que no pertenecen se rechazan — no se importa ninguno del lote
        si alguno es de otro tenant (atomicidad conceptual por lote).
        """
        # Verificar que la evaluación existe
        ev = await self.repo.get_by_id(evaluacion_id, tenant_id)
        if ev is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Convocatoria no encontrada",
            )

        # Validar pertenencia al tenant de cada alumno
        rechazados: list[uuid.UUID] = []
        validos: list[uuid.UUID] = []
        for aid in alumno_ids:
            user = await self.usuario_repo.get_by_id(aid, tenant_id=tenant_id)
            if user is None:
                rechazados.append(aid)
            else:
                validos.append(aid)

        if rechazados:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Los siguientes alumno_ids no pertenecen al tenant: {rechazados}",
            )

        total = await self.repo.import_alumnos(evaluacion_id, tenant_id, validos)
        return EvaluacionAlumnoImportResult(
            total_convocados=total,
            importados=len(validos),
            rechazados=rechazados,
        )

    # ── Reserva de turno ──────────────────────────────────────────────────────

    async def reservar_turno(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
        tenant_id: uuid.UUID,
        fecha: str,
    ) -> ReservaEvaluacionRead:
        """Reserva un turno para un ALUMNO habilitado.

        Valida:
        1. Alumno está en evaluacion_alumno → 403 si no.
        2. No tiene reserva activa → 409 si tiene.
        3. Cupo disponible → 409 si agotado (ConflictError del repo).
        """
        # 1. Verificar habilitación
        habilitado = await self.repo.is_alumno_habilitado(
            evaluacion_id, alumno_id, tenant_id
        )
        if not habilitado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El alumno no está habilitado para esta convocatoria",
            )

        # 2. Verificar reserva duplicada
        reserva_existente = await self.repo.get_reserva_activa(
            evaluacion_id, alumno_id, tenant_id
        )
        if reserva_existente is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El alumno ya tiene una reserva activa para esta convocatoria",
            )

        # 3. Reservar con control de cupo atómico
        try:
            reserva = await self.repo.reservar_turno(
                evaluacion_id, alumno_id, tenant_id, fecha
            )
        except ConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

        return ReservaEvaluacionRead(
            id=reserva.id,
            evaluacion_id=reserva.evaluacion_id,
            alumno_id=reserva.alumno_id,
            fecha=reserva.fecha,
            estado=reserva.estado,
        )

    async def cancelar_reserva(
        self,
        evaluacion_id: uuid.UUID,
        alumno_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        """Cancela la reserva activa del alumno en la evaluación.

        Valida que la reserva existe y pertenece al alumno autenticado.
        """
        reserva = await self.repo.get_reserva_activa(
            evaluacion_id, alumno_id, tenant_id
        )
        if reserva is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay reserva activa para esta convocatoria",
            )
        await self.repo.cancelar_reserva(reserva.id, tenant_id)

    # ── Métricas ──────────────────────────────────────────────────────────────

    async def get_metricas(self, tenant_id: uuid.UUID) -> MetricasColoquioRead:
        """Retorna métricas del módulo de coloquios."""
        return await self.repo.get_metricas(tenant_id)

    # ── Agenda ────────────────────────────────────────────────────────────────

    async def get_agenda(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[AgendaEntradaRead]:
        """Retorna la agenda de reservas activas de una convocatoria."""
        return await self.repo.get_agenda(evaluacion_id, tenant_id)

    # ── Resultados ────────────────────────────────────────────────────────────

    async def get_resultados(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[ResultadoEvaluacionRead]:
        """Retorna resultados de una convocatoria."""
        return await self.repo.get_resultados(evaluacion_id, tenant_id)

    async def upsert_resultado(
        self,
        evaluacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: ResultadoEvaluacionUpsert,
    ) -> ResultadoEvaluacionRead:
        """Crea o actualiza la nota final de un alumno."""
        resultado = await self.repo.upsert_resultado(
            evaluacion_id=evaluacion_id,
            alumno_id=data.alumno_id,
            tenant_id=tenant_id,
            nota_final=data.nota_final,
        )
        return ResultadoEvaluacionRead(
            id=resultado.id,
            evaluacion_id=resultado.evaluacion_id,
            alumno_id=resultado.alumno_id,
            nota_final=resultado.nota_final,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_read(ev: Evaluacion) -> EvaluacionRead:
    return EvaluacionRead(
        id=ev.id,
        tenant_id=ev.tenant_id,
        materia_id=ev.materia_id,
        cohorte_id=ev.cohorte_id,
        tipo=ev.tipo,
        instancia=ev.instancia,
        cupos_por_dia=ev.cupos_por_dia,
    )
