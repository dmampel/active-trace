"""Servicio de guardias (C-13).

Responsabilidades:
- registrar(): crea guardia con asignacion_id del JWT (NUNCA del body).
- listar(): TUTOR filtra por su asignacion_id; COORDINADOR/ADMIN obtiene todas.
- exportar_csv(): generador de filas CSV para StreamingResponse (D4).

NO accede directamente a la DB — siempre vía GuardiaRepository.
NO contiene lógica de RBAC — eso es responsabilidad de los routers.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date
from typing import AsyncGenerator, Optional

from app.models.guardia import EstadoGuardia, Guardia
from app.repositories.guardia_repository import GuardiaRepository
from app.schemas.guardia import GuardiaCreate, GuardiaFilter, GuardiaResponse

# Headers del CSV de guardias
_CSV_HEADERS = [
    "tutor",
    "materia",
    "carrera",
    "cohorte",
    "dia",
    "horario",
    "estado",
    "comentarios",
    "creada_at",
]


class GuardiaService:
    def __init__(self, repo: GuardiaRepository) -> None:
        self.repo = repo

    async def registrar(
        self,
        data: GuardiaCreate,
        *,
        asignacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> GuardiaResponse:
        """Crea una guardia con asignacion_id del JWT (regla dura #8).

        asignacion_id proviene del contexto del usuario autenticado —
        nunca del body HTTP.
        """
        guardia = Guardia(
            tenant_id=tenant_id,
            asignacion_id=asignacion_id,
            materia_id=data.materia_id,
            carrera_id=data.carrera_id,
            cohorte_id=data.cohorte_id,
            dia=data.dia,
            horario=data.horario,
            estado=data.estado,
            comentarios=data.comentarios,
        )
        guardia = await self.repo.create(guardia)
        return _guardia_to_response(guardia)

    async def listar(
        self,
        *,
        tenant_id: uuid.UUID,
        asignacion_id: Optional[uuid.UUID] = None,
        filtros: Optional[GuardiaFilter] = None,
    ) -> list[GuardiaResponse]:
        """Lista guardias según el contexto del usuario.

        Si asignacion_id está presente: filtra por esa asignación (TUTOR).
        Si asignacion_id es None: obtiene todas del tenant (COORDINADOR/ADMIN).
        """
        f = filtros or GuardiaFilter()
        if asignacion_id is not None:
            guardias = await self.repo.list_by_asignacion(
                asignacion_id,
                tenant_id,
                materia_id=f.materia_id,
                estado=f.estado,
                desde=f.desde,
                hasta=f.hasta,
            )
        else:
            guardias = await self.repo.list_all_tenant(
                tenant_id,
                materia_id=f.materia_id,
                estado=f.estado,
                desde=f.desde,
                hasta=f.hasta,
            )
        return [_guardia_to_response(g) for g in guardias]

    async def exportar_csv(
        self,
        tenant_id: uuid.UUID,
        filtros: Optional[GuardiaFilter] = None,
    ) -> AsyncGenerator[str, None]:
        """Generador de líneas CSV para StreamingResponse (D4).

        Hace yield de cada línea del CSV para evitar cargar todo en memoria.
        """
        f = filtros or GuardiaFilter()
        guardias = await self.repo.list_all_tenant(
            tenant_id,
            materia_id=f.materia_id,
            estado=f.estado,
            desde=f.desde,
            hasta=f.hasta,
        )

        # Header
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(_CSV_HEADERS)
        yield buf.getvalue()

        # Filas
        for g in guardias:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                str(g.asignacion_id),   # tutor (asignacion_id como proxy)
                str(g.materia_id),
                str(g.carrera_id) if g.carrera_id else "",
                str(g.cohorte_id) if g.cohorte_id else "",
                str(g.dia),
                g.horario,
                g.estado.value,
                g.comentarios or "",
                str(g.created_at),
            ])
            yield buf.getvalue()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _guardia_to_response(g: Guardia) -> GuardiaResponse:
    return GuardiaResponse(
        id=g.id,
        tenant_id=g.tenant_id,
        asignacion_id=g.asignacion_id,
        materia_id=g.materia_id,
        carrera_id=g.carrera_id,
        cohorte_id=g.cohorte_id,
        dia=g.dia,
        horario=g.horario,
        estado=g.estado,
        comentarios=g.comentarios,
    )
