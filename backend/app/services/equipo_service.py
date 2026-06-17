"""Service de operaciones colectivas sobre equipos docentes (C-08).

Responsabilidades:
- mis_asignaciones: vista propia del docente autenticado
- buscar_usuarios: autocompletado ILIKE para asignación masiva
- asignacion_masiva: bulk create con validación de contexto y auditoría
- clonar_equipo: clonar vigentes entre cohortes con auditoría
- actualizar_vigencia: bulk update fechas con auditoría
- exportar_csv: StreamingResponse CSV vía export_query

Reglas críticas:
- NO accede a DB directamente — usa AsignacionRepository y queries via session.
- Identidad/tenant SIEMPRE desde current_user (JWT).
- Auditoría en cada operación de mutación.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.models.user import User
from app.repositories.asignacion_repository import AsignacionRepository
from app.schemas.equipo import (
    AsignacionDetalleResponse,
    AsignacionMasivaRequest,
    AsignacionMasivaResponse,
    ClonarEquipoRequest,
    ClonarEquipoResponse,
    UsuarioBusquedaResponse,
    VigenciaEquipoRequest,
    VigenciaEquipoResponse,
)

# Audit action codes para C-08
ASIGNACION_MASIVA_CREAR = "ASIGNACION_MASIVA_CREAR"
ASIGNACION_CLONAR = "ASIGNACION_CLONAR"
ASIGNACION_VIGENCIA_BULK = "ASIGNACION_VIGENCIA_BULK"


class EquipoService:
    def __init__(self, session: AsyncSession, current_user, request=None):
        self.session = session
        self.current_user = current_user
        self.request = request

    def _repo(self) -> AsignacionRepository:
        return AsignacionRepository(self.session)

    @staticmethod
    def _derive_estado_vigencia(desde: date, hasta: Optional[date]) -> str:
        """Deriva el estado de vigencia de una asignación."""
        today = date.today()
        if desde > today:
            return "Futura"
        if hasta is not None and hasta < today:
            return "Vencida"
        return "Vigente"

    # ── 4.2: mis-asignaciones ─────────────────────────────────────────────────

    async def mis_asignaciones(
        self,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        carrera_id: Optional[uuid.UUID] = None,
        rol: Optional[str] = None,
        estado_vigencia: Optional[str] = None,
    ) -> list[AsignacionDetalleResponse]:
        """Retorna las asignaciones del usuario autenticado dentro del tenant."""
        repo = self._repo()
        rows = await repo.list_for_usuario_con_nombres(
            usuario_id=self.current_user.id,
            tenant_id=self.current_user.tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            carrera_id=carrera_id,
            rol=rol,
        )

        results = []
        for row in rows:
            estado = self._derive_estado_vigencia(row.desde, row.hasta)
            if estado_vigencia and estado != estado_vigencia:
                continue
            results.append(
                AsignacionDetalleResponse(
                    id=row.id,
                    rol=row.rol if isinstance(row.rol, str) else row.rol.value,
                    materia=row.materia_nombre,
                    carrera=row.carrera_nombre,
                    cohorte=row.cohorte_nombre,
                    desde=row.desde,
                    hasta=row.hasta,
                    estado_vigencia=estado,
                    responsable_id=row.responsable_id,
                )
            )
        return results

    # ── 4.3: buscar usuarios ──────────────────────────────────────────────────

    async def buscar_usuarios(
        self, q: str, limit: int = 20
    ) -> list[UsuarioBusquedaResponse]:
        """Busca usuarios del tenant por nombre o apellido (ILIKE)."""
        term = f"%{q}%"
        stmt = (
            select(User)
            .where(
                User.tenant_id == self.current_user.tenant_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                or_(
                    User.nombre.ilike(term),
                    User.apellidos.ilike(term),
                ),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        users = list(result.scalars().all())
        return [
            UsuarioBusquedaResponse(
                id=u.id,
                nombre=u.nombre,
                apellido=u.apellidos,
                legajo=u.legajo,
            )
            for u in users
        ]

    # ── 4.4: asignación masiva ────────────────────────────────────────────────

    async def asignacion_masiva(
        self, data: AsignacionMasivaRequest
    ) -> AsignacionMasivaResponse:
        """Crea asignaciones en bloque para múltiples usuarios."""
        tenant_id = self.current_user.tenant_id

        # Validar que todos los usuario_ids pertenecen al tenant (previene IDOR)
        count_result = await self.session.execute(
            select(func.count()).where(
                User.id.in_(data.usuario_ids),
                User.tenant_id == tenant_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )
        if count_result.scalar_one() != len(data.usuario_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uno o más usuario_ids no pertenecen al tenant o están inactivos",
            )

        # Validar contexto pertenece al tenant
        await self._validate_contexto_tenant(
            tenant_id,
            materia_id=data.materia_id,
            carrera_id=data.carrera_id,
            cohorte_id=data.cohorte_id,
        )

        items = [
            {
                "usuario_id": uid,
                "rol": data.rol,
                "desde": data.desde,
                "hasta": data.hasta,
                "materia_id": data.materia_id,
                "carrera_id": data.carrera_id,
                "cohorte_id": data.cohorte_id,
                "comisiones": [],
            }
            for uid in data.usuario_ids
        ]

        repo = self._repo()
        creadas = await repo.bulk_create(tenant_id, items)

        await record_audit(
            self.session,
            self.current_user,
            ASIGNACION_MASIVA_CREAR,
            request=self.request,
            detail={
                "creadas": creadas,
                "rol": data.rol,
                "cohorte_id": str(data.cohorte_id),
            },
            rows_affected=creadas,
        )
        return AsignacionMasivaResponse(creadas=creadas)

    # ── 4.5: clonar equipo ────────────────────────────────────────────────────

    async def clonar_equipo(self, data: ClonarEquipoRequest) -> ClonarEquipoResponse:
        """Clona asignaciones vigentes de un equipo origen a un destino."""
        tenant_id = self.current_user.tenant_id

        # Validar origen != destino
        if (
            data.origen.cohorte_id == data.destino.cohorte_id
            and data.origen.materia_id == data.destino.materia_id
            and data.origen.carrera_id == data.destino.carrera_id
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El equipo origen y destino no pueden ser idénticos",
            )

        # Validar ambos contextos pertenecen al tenant
        await self._validate_contexto_tenant(
            tenant_id,
            cohorte_id=data.origen.cohorte_id,
            materia_id=data.origen.materia_id,
            carrera_id=data.origen.carrera_id,
        )
        await self._validate_contexto_tenant(
            tenant_id,
            cohorte_id=data.destino.cohorte_id,
            materia_id=data.destino.materia_id,
            carrera_id=data.destino.carrera_id,
        )

        repo = self._repo()
        clonadas, omitidas = await repo.clone(
            tenant_id,
            origen={
                "cohorte_id": data.origen.cohorte_id,
                "materia_id": data.origen.materia_id,
                "carrera_id": data.origen.carrera_id,
            },
            destino={
                "cohorte_id": data.destino.cohorte_id,
                "materia_id": data.destino.materia_id,
                "carrera_id": data.destino.carrera_id,
            },
        )

        await record_audit(
            self.session,
            self.current_user,
            ASIGNACION_CLONAR,
            request=self.request,
            detail={
                "clonadas": clonadas,
                "omitidas": omitidas,
                "origen_cohorte": str(data.origen.cohorte_id),
                "destino_cohorte": str(data.destino.cohorte_id),
            },
            rows_affected=clonadas,
        )
        return ClonarEquipoResponse(clonadas=clonadas, omitidas=omitidas)

    # ── 4.6: actualizar vigencia ──────────────────────────────────────────────

    async def actualizar_vigencia(
        self, data: VigenciaEquipoRequest
    ) -> VigenciaEquipoResponse:
        """Actualiza desde/hasta de todas las asignaciones de un equipo."""
        # Validar schema ya garantiza al menos uno de desde/hasta — refuerzo en service
        if data.desde is None and data.hasta is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Al menos uno de 'desde' o 'hasta' debe estar presente",
            )

        tenant_id = self.current_user.tenant_id
        repo = self._repo()
        actualizadas = await repo.bulk_update_vigencia(
            tenant_id,
            filtro={
                "cohorte_id": data.cohorte_id,
                "materia_id": data.materia_id,
                "carrera_id": data.carrera_id,
            },
            desde=data.desde,
            hasta=data.hasta,
        )

        await record_audit(
            self.session,
            self.current_user,
            ASIGNACION_VIGENCIA_BULK,
            request=self.request,
            detail={
                "actualizadas": actualizadas,
                "cohorte_id": str(data.cohorte_id),
            },
            rows_affected=actualizadas,
        )
        return VigenciaEquipoResponse(actualizadas=actualizadas)

    # ── 4.7: exportar CSV ─────────────────────────────────────────────────────

    async def exportar_csv(self) -> StreamingResponse:
        """Retorna StreamingResponse CSV con el plantel docente del tenant."""
        tenant_id = self.current_user.tenant_id
        repo = self._repo()
        rows = await repo.export_query(tenant_id)

        def _generate():
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                "nombre", "apellido", "legajo", "rol",
                "materia", "carrera", "cohorte", "desde", "hasta", "estado_vigencia",
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

            today = date.today()
            for row in rows:
                nombre, apellidos, legajo, rol, materia_nombre, carrera_nombre, cohorte_nombre, desde, hasta = row
                if desde > today:
                    estado = "Futura"
                elif hasta is not None and hasta < today:
                    estado = "Vencida"
                else:
                    estado = "Vigente"

                writer.writerow([
                    nombre or "",
                    apellidos or "",
                    legajo or "",
                    rol if isinstance(rol, str) else rol.value,
                    materia_nombre or "",
                    carrera_nombre or "",
                    cohorte_nombre or "",
                    str(desde),
                    str(hasta) if hasta else "",
                    estado,
                ])
                yield buf.getvalue()
                buf.seek(0)
                buf.truncate(0)

        return StreamingResponse(
            _generate(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="equipo.csv"'},
        )

    # ── Helpers de validación ─────────────────────────────────────────────────

    async def _validate_contexto_tenant(
        self,
        tenant_id: uuid.UUID,
        cohorte_id: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
        carrera_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Valida que los IDs de contexto pertenezcan al tenant. Lanza 422 si no."""
        from app.models.estructura import Carrera, Cohorte, Materia

        if cohorte_id is not None:
            result = await self.session.execute(
                select(Cohorte.id).where(
                    Cohorte.id == cohorte_id,
                    Cohorte.tenant_id == tenant_id,
                    Cohorte.deleted_at.is_(None),
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"cohorte_id {cohorte_id} no pertenece al tenant",
                )

        if materia_id is not None:
            result = await self.session.execute(
                select(Materia.id).where(
                    Materia.id == materia_id,
                    Materia.tenant_id == tenant_id,
                    Materia.deleted_at.is_(None),
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"materia_id {materia_id} no pertenece al tenant",
                )

        if carrera_id is not None:
            result = await self.session.execute(
                select(Carrera.id).where(
                    Carrera.id == carrera_id,
                    Carrera.tenant_id == tenant_id,
                    Carrera.deleted_at.is_(None),
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"carrera_id {carrera_id} no pertenece al tenant",
                )
