"""Service de asignaciones contextuales.

Responsabilidades:
- Validación de contexto (materia_id/carrera_id/cohorte_id) contra tenant
- Jerarquía responsable_id
- Derivación de estado_vigencia (no almacenado)
- Auditoría ASIGNACION_MODIFICAR en create/update/delete
- Soporte multi-rol (un usuario puede tener múltiples asignaciones)

Regla crítica: NO accede a la DB directamente — usa AsignacionRepository.
"""
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import ASIGNACION_MODIFICAR, record_audit
from app.repositories.asignacion_repository import AsignacionRepository
from app.schemas.asignacion import AsignacionRead


class AsignacionService:
    def __init__(self, session: AsyncSession, current_user, request=None):
        self.session = session
        self.current_user = current_user
        self.request = request

    def _repo(self) -> AsignacionRepository:
        return AsignacionRepository(self.session)

    def _to_read_dto(self, asig) -> AsignacionRead:
        repo = self._repo()
        estado_vigencia = repo.derive_estado_vigencia(asig)
        return AsignacionRead(
            id=asig.id,
            tenant_id=asig.tenant_id,
            usuario_id=asig.usuario_id,
            rol=asig.rol if isinstance(asig.rol, str) else asig.rol.value,
            desde=asig.desde,
            hasta=asig.hasta,
            materia_id=asig.materia_id,
            carrera_id=asig.carrera_id,
            cohorte_id=asig.cohorte_id,
            comisiones=asig.comisiones or [],
            responsable_id=asig.responsable_id,
            estado_vigencia=estado_vigencia,
        )

    async def create(self, data: dict) -> AsignacionRead:
        """Crea una asignación con auditoría."""
        repo = self._repo()
        asig = await repo.create(self.current_user.tenant_id, data)
        await record_audit(
            self.session,
            self.current_user,
            ASIGNACION_MODIFICAR,
            request=self.request,
            detail={"asignacion_id": str(asig.id), "accion": "create"},
        )
        return self._to_read_dto(asig)

    async def list_asignaciones(
        self,
        usuario_id: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        rol: Optional[str] = None,
        vigente_only: bool = False,
    ) -> list[AsignacionRead]:
        repo = self._repo()
        asigs = await repo.list(
            self.current_user.tenant_id,
            usuario_id=usuario_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            rol=rol,
            vigente_only=vigente_only,
        )
        return [self._to_read_dto(a) for a in asigs]

    async def get_detail(self, asig_id: uuid.UUID) -> AsignacionRead:
        repo = self._repo()
        asig = await repo.get_by_id(asig_id, self.current_user.tenant_id)
        if not asig:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Asignación no encontrada")
        return self._to_read_dto(asig)

    async def update(self, asig_id: uuid.UUID, data: dict) -> AsignacionRead:
        repo = self._repo()
        asig = await repo.update(asig_id, self.current_user.tenant_id, data)
        if not asig:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Asignación no encontrada")
        await record_audit(
            self.session,
            self.current_user,
            ASIGNACION_MODIFICAR,
            request=self.request,
            detail={"asignacion_id": str(asig_id), "accion": "update"},
        )
        return self._to_read_dto(asig)

    async def soft_delete(self, asig_id: uuid.UUID) -> None:
        repo = self._repo()
        found = await repo.soft_delete(asig_id, self.current_user.tenant_id)
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Asignación no encontrada")
        await record_audit(
            self.session,
            self.current_user,
            ASIGNACION_MODIFICAR,
            request=self.request,
            detail={"asignacion_id": str(asig_id), "accion": "delete"},
        )
