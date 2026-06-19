"""Servicio para el módulo de tareas internas (C-16).

Responsabilidades:
- Orquestar CRUD de Tarea delegando a TareaRepository y ComentarioTareaRepository.
- Validar que asignado_a pertenezca al tenant antes de crear.
- Hacer cumplir la máquina de estados (TRANSICIONES).
- Validar autorización en cambios de estado (involucrados o COORDINADOR/ADMIN).
- Restringir la vista global a COORDINADOR/ADMIN.

NO accede directamente a la DB — siempre vía repositorios.
NO contiene lógica de RBAC de endpoint — eso es responsabilidad de los routers.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status

from app.models.tarea import EstadoTarea, Tarea
from app.repositories.tarea_repository import ComentarioTareaRepository, TareaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.tarea import ComentarioOut, PaginatedTareas, TareaCreate, TareaOut

# ── Máquina de estados (D1) ───────────────────────────────────────────────────

TRANSICIONES: dict[str, set[str]] = {
    "pendiente": {"en_progreso", "cancelada"},
    "en_progreso": {"resuelta", "cancelada", "pendiente"},
    "resuelta": set(),
    "cancelada": set(),
}

# Roles que pueden cambiar el estado de cualquier tarea del tenant
_ROLES_ADMIN = {"COORDINADOR", "ADMIN"}


class TareaService:
    def __init__(
        self,
        tarea_repo: TareaRepository,
        comentario_repo: ComentarioTareaRepository,
        usuario_repo: UsuarioRepository,
    ) -> None:
        self.repo = tarea_repo
        self.comentario_repo = comentario_repo
        self.usuario_repo = usuario_repo

    # ── crear_tarea ───────────────────────────────────────────────────────────

    async def crear_tarea(
        self,
        tenant_id: uuid.UUID,
        asignado_por: uuid.UUID,
        data: TareaCreate,
    ) -> TareaOut:
        """Crea una tarea. Valida que asignado_a pertenezca al tenant."""
        destinatario = await self.usuario_repo.get_by_id(data.asignado_a, tenant_id)
        if destinatario is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario asignado no pertenece al tenant",
            )
        tarea = await self.repo.create(tenant_id, asignado_por, data)
        return TareaOut.model_validate(tarea)

    # ── cambiar_estado ────────────────────────────────────────────────────────

    async def cambiar_estado(
        self,
        tenant_id: uuid.UUID,
        tarea_id: uuid.UUID,
        nuevo_estado: EstadoTarea,
        usuario_id: uuid.UUID,
        roles: list[str],
    ) -> TareaOut:
        """Cambia el estado de una tarea.

        Valida:
        1. La tarea existe en el tenant.
        2. La transición es válida.
        3. El usuario está autorizado (involucrado o COORDINADOR/ADMIN).
        """
        tarea = await self.repo.get_by_id(tenant_id, tarea_id)
        if tarea is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada",
            )

        self._validar_transicion(tarea.estado, nuevo_estado)

        # Autorización: involucrados o roles admin
        es_involucrado = usuario_id in (tarea.asignado_a, tarea.asignado_por)
        es_admin = bool(_ROLES_ADMIN.intersection(roles))
        if not es_involucrado and not es_admin:
            raise PermissionError(
                "Solo los involucrados o COORDINADOR/ADMIN pueden cambiar el estado"
            )

        tarea_actualizada = await self.repo.update_estado(tenant_id, tarea_id, nuevo_estado)
        if tarea_actualizada is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada",
            )
        return TareaOut.model_validate(tarea_actualizada)

    # ── agregar_comentario ────────────────────────────────────────────────────

    async def agregar_comentario(
        self,
        tenant_id: uuid.UUID,
        tarea_id: uuid.UUID,
        autor_id: uuid.UUID,
        texto: str,
    ) -> ComentarioOut:
        """Agrega un comentario a una tarea. Valida que la tarea exista en el tenant."""
        tarea = await self.repo.get_by_id(tenant_id, tarea_id)
        if tarea is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada",
            )
        comentario = await self.comentario_repo.create(tenant_id, tarea_id, autor_id, texto)
        return ComentarioOut.model_validate(comentario)

    # ── mis_tareas ────────────────────────────────────────────────────────────

    async def mis_tareas(
        self,
        tenant_id: uuid.UUID,
        asignado_a: uuid.UUID,
        estado: Optional[EstadoTarea] = None,
    ) -> list[TareaOut]:
        """Retorna las tareas asignadas al usuario, opcionalmente filtradas por estado."""
        tareas = await self.repo.list_mis_tareas(tenant_id, asignado_a, estado)
        return [TareaOut.model_validate(t) for t in tareas]

    # ── listar_todas ──────────────────────────────────────────────────────────

    async def listar_todas(
        self,
        tenant_id: uuid.UUID,
        roles: list[str],
        filters: dict,
        page: int,
        size: int,
    ) -> PaginatedTareas:
        """Vista global de tareas del tenant. Solo COORDINADOR/ADMIN."""
        if not _ROLES_ADMIN.intersection(roles):
            raise PermissionError(
                "Solo COORDINADOR o ADMIN pueden acceder a la vista global de tareas"
            )
        items, total = await self.repo.list_all(tenant_id, filters, page, size)
        return PaginatedTareas(
            total=total,
            page=page,
            size=size,
            items=[TareaOut.model_validate(t) for t in items],
        )

    # ── listar_comentarios ────────────────────────────────────────────────────

    async def listar_comentarios(
        self,
        tenant_id: uuid.UUID,
        tarea_id: uuid.UUID,
    ) -> list[ComentarioOut]:
        """Lista los comentarios de una tarea en orden cronológico."""
        tarea = await self.repo.get_by_id(tenant_id, tarea_id)
        if tarea is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada",
            )
        comentarios = await self.comentario_repo.list_comentarios(tenant_id, tarea_id)
        return [ComentarioOut.model_validate(c) for c in comentarios]

    # ── helpers privados ──────────────────────────────────────────────────────

    def _validar_transicion(
        self,
        estado_actual: EstadoTarea,
        nuevo_estado: EstadoTarea,
    ) -> None:
        """Lanza ValueError si la transición no es válida según TRANSICIONES."""
        permitidos = TRANSICIONES.get(estado_actual.value, set())
        if nuevo_estado.value not in permitidos:
            raise ValueError(
                f"Transición inválida: {estado_actual.value} → {nuevo_estado.value}. "
                f"Transiciones permitidas: {permitidos or '(ninguna — estado terminal)'}"
            )
