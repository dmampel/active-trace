import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, get_current_user, get_sync_db
from app.core.permissions import require_permission
from app.schemas.estructura import (
    CarreraCreate, CarreraRead, CarreraUpdate,
    CohorteCreate, CohorteRead, CohorteUpdate,
    InstanciaCreate, InstanciaRead, InstanciaUpdate,
    MateriaCreate, MateriaRead, MateriaUpdate,
)
from app.services.estructura_service import EstructuraService

router = APIRouter(prefix="/api/v1/estructura", tags=["estructura"])


def _svc(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> EstructuraService:
    return EstructuraService(db, current_user, request)


# ── Carreras ──────────────────────────────────────────────────────────────────

@router.post("/carreras", response_model=CarreraRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("estructura:crear"))])
def create_carrera(body: CarreraCreate, svc: EstructuraService = Depends(_svc)):
    return svc.create_carrera(body.model_dump())


@router.get("/carreras", response_model=List[CarreraRead],
            dependencies=[Depends(require_permission("estructura:leer"))])
def list_carreras(svc: EstructuraService = Depends(_svc)):
    return svc.list_carreras()


@router.get("/carreras/{id}", response_model=CarreraRead,
            dependencies=[Depends(require_permission("estructura:leer"))])
def get_carrera(id: uuid.UUID, svc: EstructuraService = Depends(_svc)):
    return svc.get_carrera(id)


@router.patch("/carreras/{id}", response_model=CarreraRead,
              dependencies=[Depends(require_permission("estructura:editar"))])
def update_carrera(id: uuid.UUID, body: CarreraUpdate, svc: EstructuraService = Depends(_svc)):
    return svc.update_carrera(id, body.model_dump(exclude_none=True))


@router.delete("/carreras/{id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("estructura:eliminar"))])
def delete_carrera(id: uuid.UUID, svc: EstructuraService = Depends(_svc)):
    svc.delete_carrera(id)


# ── Cohortes ──────────────────────────────────────────────────────────────────

@router.post("/cohortes", response_model=CohorteRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("estructura:crear"))])
def create_cohorte(body: CohorteCreate, svc: EstructuraService = Depends(_svc)):
    return svc.create_cohorte(body.model_dump())


@router.get("/cohortes", response_model=List[CohorteRead],
            dependencies=[Depends(require_permission("estructura:leer"))])
def list_cohortes(carrera_id: Optional[uuid.UUID] = None, svc: EstructuraService = Depends(_svc)):
    return svc.list_cohortes(carrera_id=carrera_id)


@router.get("/cohortes/{id}", response_model=CohorteRead,
            dependencies=[Depends(require_permission("estructura:leer"))])
def get_cohorte(id: uuid.UUID, svc: EstructuraService = Depends(_svc)):
    return svc.get_cohorte(id)


@router.patch("/cohortes/{id}", response_model=CohorteRead,
              dependencies=[Depends(require_permission("estructura:editar"))])
def update_cohorte(id: uuid.UUID, body: CohorteUpdate, svc: EstructuraService = Depends(_svc)):
    return svc.update_cohorte(id, body.model_dump(exclude_none=True))


@router.delete("/cohortes/{id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("estructura:eliminar"))])
def delete_cohorte(id: uuid.UUID, svc: EstructuraService = Depends(_svc)):
    svc.delete_cohorte(id)


# ── Materias ──────────────────────────────────────────────────────────────────

@router.post("/materias", response_model=MateriaRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("estructura:crear"))])
def create_materia(body: MateriaCreate, svc: EstructuraService = Depends(_svc)):
    return svc.create_materia(body.model_dump())


@router.get("/materias", response_model=List[MateriaRead],
            dependencies=[Depends(require_permission("estructura:leer"))])
def list_materias(svc: EstructuraService = Depends(_svc)):
    return svc.list_materias()


@router.get("/materias/{id}", response_model=MateriaRead,
            dependencies=[Depends(require_permission("estructura:leer"))])
def get_materia(id: uuid.UUID, svc: EstructuraService = Depends(_svc)):
    return svc.get_materia(id)


@router.patch("/materias/{id}", response_model=MateriaRead,
              dependencies=[Depends(require_permission("estructura:editar"))])
def update_materia(id: uuid.UUID, body: MateriaUpdate, svc: EstructuraService = Depends(_svc)):
    return svc.update_materia(id, body.model_dump(exclude_none=True))


@router.delete("/materias/{id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("estructura:eliminar"))])
def delete_materia(id: uuid.UUID, svc: EstructuraService = Depends(_svc)):
    svc.delete_materia(id)


# ── Instancias de dictado ─────────────────────────────────────────────────────

@router.post("/instancias", response_model=InstanciaRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("estructura:crear"))])
def create_instancia(body: InstanciaCreate, svc: EstructuraService = Depends(_svc)):
    return svc.create_instancia(body.model_dump())


@router.get("/instancias", response_model=List[InstanciaRead],
            dependencies=[Depends(require_permission("estructura:leer"))])
def list_instancias(
    cohorte_id: Optional[uuid.UUID] = None,
    materia_id: Optional[uuid.UUID] = None,
    svc: EstructuraService = Depends(_svc),
):
    return svc.list_instancias(cohorte_id=cohorte_id, materia_id=materia_id)


@router.get("/instancias/{id}", response_model=InstanciaRead,
            dependencies=[Depends(require_permission("estructura:leer"))])
def get_instancia(id: uuid.UUID, svc: EstructuraService = Depends(_svc)):
    return svc.get_instancia(id)


@router.patch("/instancias/{id}", response_model=InstanciaRead,
              dependencies=[Depends(require_permission("estructura:editar"))])
def update_instancia(id: uuid.UUID, body: InstanciaUpdate, svc: EstructuraService = Depends(_svc)):
    return svc.update_instancia(id, body.model_dump(exclude_none=True))


@router.delete("/instancias/{id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("estructura:eliminar"))])
def delete_instancia(id: uuid.UUID, svc: EstructuraService = Depends(_svc)):
    svc.delete_instancia(id)
