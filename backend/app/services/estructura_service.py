import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import record_audit_sync
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


def _carrera_repo(session):
    from app.repositories.estructura_repository import CarreraRepository
    return CarreraRepository(session)


def _cohorte_repo(session):
    from app.repositories.estructura_repository import CohorteRepository
    return CohorteRepository(session)


def _materia_repo(session):
    from app.repositories.estructura_repository import MateriaRepository
    return MateriaRepository(session)


def _instancia_repo(session):
    from app.repositories.estructura_repository import InstanciaDictadoRepository
    return InstanciaDictadoRepository(session)


class EstructuraService:
    def __init__(self, session: Session, current_user, request=None):
        self.session = session
        self.current_user = current_user
        self.request = request

    # ── Carrera ───────────────────────────────────────────────────────────────

    def create_carrera(self, data: dict) -> Carrera:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            carrera = loop.run_until_complete(
                _carrera_repo(self.session).create(self.current_user.tenant_id, data)
            )
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Código ya existe en el tenant")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_CARRERA_CREAR,
                          request=self.request, detail={"codigo": data.get("codigo")})
        return carrera

    def list_carreras(self) -> list:
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_carrera_repo(self.session).list_active(self.current_user.tenant_id))

    def get_carrera(self, id: uuid.UUID) -> Carrera:
        import asyncio
        loop = asyncio.get_event_loop()
        obj = loop.run_until_complete(_carrera_repo(self.session).get_by_id(id, self.current_user.tenant_id))
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carrera no encontrada")
        return obj

    def update_carrera(self, id: uuid.UUID, data: dict) -> Carrera:
        import asyncio
        loop = asyncio.get_event_loop()
        obj = loop.run_until_complete(_carrera_repo(self.session).update(id, self.current_user.tenant_id, data))
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carrera no encontrada")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_CARRERA_EDITAR,
                          request=self.request, detail={"id": str(id)})
        return obj

    def delete_carrera(self, id: uuid.UUID) -> None:
        import asyncio
        loop = asyncio.get_event_loop()
        found = loop.run_until_complete(_carrera_repo(self.session).soft_delete(id, self.current_user.tenant_id))
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carrera no encontrada")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_CARRERA_ELIMINAR,
                          request=self.request, detail={"id": str(id)})

    # ── Cohorte ───────────────────────────────────────────────────────────────

    def create_cohorte(self, data: dict) -> Cohorte:
        import asyncio
        loop = asyncio.get_event_loop()
        carrera_id = data.get("carrera_id")
        if carrera_id:
            carrera = loop.run_until_complete(
                _carrera_repo(self.session).get_by_id(carrera_id, self.current_user.tenant_id)
            )
            if not carrera:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="carrera_id inválido o no pertenece al tenant")
        try:
            cohorte = loop.run_until_complete(
                _cohorte_repo(self.session).create(self.current_user.tenant_id, data)
            )
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cohorte ya existe")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_COHORTE_CREAR,
                          request=self.request, detail={"nombre": data.get("nombre")})
        return cohorte

    def list_cohortes(self, carrera_id: Optional[uuid.UUID] = None) -> list:
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            _cohorte_repo(self.session).list_active(self.current_user.tenant_id, carrera_id=carrera_id)
        )

    def get_cohorte(self, id: uuid.UUID) -> Cohorte:
        import asyncio
        loop = asyncio.get_event_loop()
        obj = loop.run_until_complete(_cohorte_repo(self.session).get_by_id(id, self.current_user.tenant_id))
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohorte no encontrada")
        return obj

    def update_cohorte(self, id: uuid.UUID, data: dict) -> Cohorte:
        import asyncio
        loop = asyncio.get_event_loop()
        obj = loop.run_until_complete(_cohorte_repo(self.session).update(id, self.current_user.tenant_id, data))
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohorte no encontrada")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_COHORTE_EDITAR,
                          request=self.request, detail={"id": str(id)})
        return obj

    def delete_cohorte(self, id: uuid.UUID) -> None:
        import asyncio
        loop = asyncio.get_event_loop()
        found = loop.run_until_complete(_cohorte_repo(self.session).soft_delete(id, self.current_user.tenant_id))
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohorte no encontrada")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_COHORTE_ELIMINAR,
                          request=self.request, detail={"id": str(id)})

    # ── Materia ───────────────────────────────────────────────────────────────

    def create_materia(self, data: dict) -> Materia:
        import asyncio
        loop = asyncio.get_event_loop()
        try:
            materia = loop.run_until_complete(
                _materia_repo(self.session).create(self.current_user.tenant_id, data)
            )
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Código ya existe en el tenant")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_MATERIA_CREAR,
                          request=self.request, detail={"codigo": data.get("codigo")})
        return materia

    def list_materias(self) -> list:
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_materia_repo(self.session).list_active(self.current_user.tenant_id))

    def get_materia(self, id: uuid.UUID) -> Materia:
        import asyncio
        loop = asyncio.get_event_loop()
        obj = loop.run_until_complete(_materia_repo(self.session).get_by_id(id, self.current_user.tenant_id))
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materia no encontrada")
        return obj

    def update_materia(self, id: uuid.UUID, data: dict) -> Materia:
        import asyncio
        loop = asyncio.get_event_loop()
        obj = loop.run_until_complete(_materia_repo(self.session).update(id, self.current_user.tenant_id, data))
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materia no encontrada")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_MATERIA_EDITAR,
                          request=self.request, detail={"id": str(id)})
        return obj

    def delete_materia(self, id: uuid.UUID) -> None:
        import asyncio
        loop = asyncio.get_event_loop()
        found = loop.run_until_complete(_materia_repo(self.session).soft_delete(id, self.current_user.tenant_id))
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Materia no encontrada")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_MATERIA_ELIMINAR,
                          request=self.request, detail={"id": str(id)})

    # ── InstanciaDictado ──────────────────────────────────────────────────────

    def create_instancia(self, data: dict) -> InstanciaDictado:
        import asyncio
        loop = asyncio.get_event_loop()
        materia_id = data.get("materia_id")
        cohorte_id = data.get("cohorte_id")
        if materia_id:
            m = loop.run_until_complete(
                _materia_repo(self.session).get_by_id(materia_id, self.current_user.tenant_id)
            )
            if not m:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="materia_id inválido o no pertenece al tenant")
        if cohorte_id:
            c = loop.run_until_complete(
                _cohorte_repo(self.session).get_by_id(cohorte_id, self.current_user.tenant_id)
            )
            if not c:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="cohorte_id inválido o no pertenece al tenant")
        try:
            instancia = loop.run_until_complete(
                _instancia_repo(self.session).create(self.current_user.tenant_id, data)
            )
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instancia ya existe para esa combinación")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_INSTANCIA_CREAR,
                          request=self.request, detail={"periodo": data.get("periodo")})
        return instancia

    def list_instancias(self, cohorte_id: Optional[uuid.UUID] = None, materia_id: Optional[uuid.UUID] = None) -> list:
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            _instancia_repo(self.session).list_active(
                self.current_user.tenant_id, cohorte_id=cohorte_id, materia_id=materia_id
            )
        )

    def get_instancia(self, id: uuid.UUID) -> InstanciaDictado:
        import asyncio
        loop = asyncio.get_event_loop()
        obj = loop.run_until_complete(_instancia_repo(self.session).get_by_id(id, self.current_user.tenant_id))
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia no encontrada")
        return obj

    def update_instancia(self, id: uuid.UUID, data: dict) -> InstanciaDictado:
        import asyncio
        loop = asyncio.get_event_loop()
        obj = loop.run_until_complete(_instancia_repo(self.session).update(id, self.current_user.tenant_id, data))
        if not obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia no encontrada")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_INSTANCIA_EDITAR,
                          request=self.request, detail={"id": str(id)})
        return obj

    def delete_instancia(self, id: uuid.UUID) -> None:
        import asyncio
        loop = asyncio.get_event_loop()
        found = loop.run_until_complete(_instancia_repo(self.session).soft_delete(id, self.current_user.tenant_id))
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia no encontrada")
        record_audit_sync(self.session, self.current_user, ESTRUCTURA_INSTANCIA_ELIMINAR,
                          request=self.request, detail={"id": str(id)})
