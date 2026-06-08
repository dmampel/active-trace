import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.models.estructura import Carrera, Cohorte, InstanciaDictado, Materia

ESTRUCTURA_CARRERA_CREAR = "ESTRUCTURA_CARRERA_CREAR"
ESTRUCTURA_CARRERA_EDITAR = "ESTRUCTURA_CARRERA_EDITAR"
ESTRUCTURA_CARRERA_ELIMINAR = "ESTRUCTURA_CARRERA_ELIMINAR"
ESTRUCTURA_COHORTE_CREAR = "ESTRUCTURA_COHORTE_CREAR"
ESTRUCTURA_COHORTE_EDITAR = "ESTRUCTURA_COHORTE_EDITAR"
ESTRUCTURA_COHORTE_ELIMINAR = "ESTRUCTURA_COHORTE_ELIMINAR"
ESTRUCTURA_MATERIA_CREAR = "ESTRUCTURA_MATERIA_CREAR"
ESTRUCTURA_MATERIA_EDITAR = "ESTRUCTURA_MATERIA_EDITAR"
ESTRUCTURA_MATERIA_ELIMINAR = "ESTRUCTURA_MATERIA_ELIMINAR"
ESTRUCTURA_INSTANCIA_CREAR = "ESTRUCTURA_INSTANCIA_CREAR"
ESTRUCTURA_INSTANCIA_EDITAR = "ESTRUCTURA_INSTANCIA_EDITAR"
ESTRUCTURA_INSTANCIA_ELIMINAR = "ESTRUCTURA_INSTANCIA_ELIMINAR"


class EstructuraService:
    def __init__(self, session: AsyncSession, current_user, request=None):
        self.session = session
        self.current_user = current_user
        self.request = request

    def _carrera_repo(self):
        from app.repositories.estructura_repository import CarreraRepository
        return CarreraRepository(self.session)

    def _cohorte_repo(self):
        from app.repositories.estructura_repository import CohorteRepository
        return CohorteRepository(self.session)

    def _materia_repo(self):
        from app.repositories.estructura_repository import MateriaRepository
        return MateriaRepository(self.session)

    def _instancia_repo(self):
        from app.repositories.estructura_repository import InstanciaDictadoRepository
        return InstanciaDictadoRepository(self.session)

    # ── Carrera ───────────────────────────────────────────────────────────────

    async def create_carrera(self, data: dict) -> Carrera:
        try:
            carrera = await self._carrera_repo().create(self.current_user.tenant_id, data)
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Código ya existe en el tenant")
        await record_audit(self.session, self.current_user, ESTRUCTURA_CARRERA_CREAR,
                           request=self.request, detail={"codigo": data.get("codigo")})
        return carrera

    async def list_carreras(self) -> list:
        return await self._carrera_repo().list_active(self.current_user.tenant_id)

    async def get_carrera(self, id: uuid.UUID) -> Carrera:
        obj = await self._carrera_repo().get_by_id(id, self.current_user.tenant_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carrera no encontrada")
        return obj

    async def update_carrera(self, id: uuid.UUID, data: dict) -> Carrera:
        obj = await self._carrera_repo().update(id, self.current_user.tenant_id, data)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carrera no encontrada")
        await record_audit(self.session, self.current_user, ESTRUCTURA_CARRERA_EDITAR,
                           request=self.request, detail={"id": str(id)})
        return obj

    async def delete_carrera(self, id: uuid.UUID) -> None:
        found = await self._carrera_repo().soft_delete(id, self.current_user.tenant_id)
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carrera no encontrada")
        await record_audit(self.session, self.current_user, ESTRUCTURA_CARRERA_ELIMINAR,
                           request=self.request, detail={"id": str(id)})

    # ── Cohorte ───────────────────────────────────────────────────────────────

    async def create_cohorte(self, data: dict) -> Cohorte:
        carrera_id = data.get("carrera_id")
        if carrera_id:
            carrera = await self._carrera_repo().get_by_id(carrera_id, self.current_user.tenant_id)
            if not carrera:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="carrera_id inválido o no pertenece al tenant")
        try:
            cohorte = await self._cohorte_repo().create(self.current_user.tenant_id, data)
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cohorte ya existe")
        await record_audit(self.session, self.current_user, ESTRUCTURA_COHORTE_CREAR,
                           request=self.request, detail={"nombre": data.get("nombre")})
        return cohorte

    async def list_cohortes(self, carrera_id: Optional[uuid.UUID] = None) -> list:
        return await self._cohorte_repo().list_active(self.current_user.tenant_id, carrera_id=carrera_id)

    async def get_cohorte(self, id: uuid.UUID) -> Cohorte:
        obj = await self._cohorte_repo().get_by_id(id, self.current_user.tenant_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohorte no encontrada")
        return obj

    async def update_cohorte(self, id: uuid.UUID, data: dict) -> Cohorte:
        obj = await self._cohorte_repo().update(id, self.current_user.tenant_id, data)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohorte no encontrada")
        await record_audit(self.session, self.current_user, ESTRUCTURA_COHORTE_EDITAR,
                           request=self.request, detail={"id": str(id)})
        return obj

    async def delete_cohorte(self, id: uuid.UUID) -> None:
        found = await self._cohorte_repo().soft_delete(id, self.current_user.tenant_id)
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohorte no encontrada")
        await record_audit(self.session, self.current_user, ESTRUCTURA_COHORTE_ELIMINAR,
                           request=self.request, detail={"id": str(id)})

    # ── Materia ───────────────────────────────────────────────────────────────

    async def create_materia(self, data: dict) -> Materia:
        try:
            materia = await self._materia_repo().create(self.current_user.tenant_id, data)
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Código ya existe en el tenant")
        await record_audit(self.session, self.current_user, ESTRUCTURA_MATERIA_CREAR,
                           request=self.request, detail={"codigo": data.get("codigo")})
        return materia

    async def list_materias(self) -> list:
        return await self._materia_repo().list_active(self.current_user.tenant_id)

    async def get_materia(self, id: uuid.UUID) -> Materia:
        obj = await self._materia_repo().get_by_id(id, self.current_user.tenant_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materia no encontrada")
        return obj

    async def update_materia(self, id: uuid.UUID, data: dict) -> Materia:
        obj = await self._materia_repo().update(id, self.current_user.tenant_id, data)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materia no encontrada")
        await record_audit(self.session, self.current_user, ESTRUCTURA_MATERIA_EDITAR,
                           request=self.request, detail={"id": str(id)})
        return obj

    async def delete_materia(self, id: uuid.UUID) -> None:
        found = await self._materia_repo().soft_delete(id, self.current_user.tenant_id)
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materia no encontrada")
        await record_audit(self.session, self.current_user, ESTRUCTURA_MATERIA_ELIMINAR,
                           request=self.request, detail={"id": str(id)})

    # ── InstanciaDictado ──────────────────────────────────────────────────────

    async def create_instancia(self, data: dict) -> InstanciaDictado:
        materia_id = data.get("materia_id")
        cohorte_id = data.get("cohorte_id")
        if materia_id:
            m = await self._materia_repo().get_by_id(materia_id, self.current_user.tenant_id)
            if not m:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="materia_id inválido o no pertenece al tenant")
        if cohorte_id:
            c = await self._cohorte_repo().get_by_id(cohorte_id, self.current_user.tenant_id)
            if not c:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="cohorte_id inválido o no pertenece al tenant")
        try:
            instancia = await self._instancia_repo().create(self.current_user.tenant_id, data)
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instancia ya existe para esa combinación")
        await record_audit(self.session, self.current_user, ESTRUCTURA_INSTANCIA_CREAR,
                           request=self.request, detail={"periodo": data.get("periodo")})
        return instancia

    async def list_instancias(self, cohorte_id: Optional[uuid.UUID] = None, materia_id: Optional[uuid.UUID] = None) -> list:
        return await self._instancia_repo().list_active(
            self.current_user.tenant_id, cohorte_id=cohorte_id, materia_id=materia_id
        )

    async def get_instancia(self, id: uuid.UUID) -> InstanciaDictado:
        obj = await self._instancia_repo().get_by_id(id, self.current_user.tenant_id)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia no encontrada")
        return obj

    async def update_instancia(self, id: uuid.UUID, data: dict) -> InstanciaDictado:
        obj = await self._instancia_repo().update(id, self.current_user.tenant_id, data)
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia no encontrada")
        await record_audit(self.session, self.current_user, ESTRUCTURA_INSTANCIA_EDITAR,
                           request=self.request, detail={"id": str(id)})
        return obj

    async def delete_instancia(self, id: uuid.UUID) -> None:
        found = await self._instancia_repo().soft_delete(id, self.current_user.tenant_id)
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia no encontrada")
        await record_audit(self.session, self.current_user, ESTRUCTURA_INSTANCIA_ELIMINAR,
                           request=self.request, detail={"id": str(id)})
