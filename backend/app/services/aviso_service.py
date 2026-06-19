"""Servicio para el módulo de avisos y acknowledgment (C-15).

Responsabilidades:
- Orquestar CRUD de Aviso delegando a AvisoRepository.
- get_mis_avisos(): resuelve asignaciones activas del usuario para inyectar
  materias_ids y cohortes_ids al repositorio.
- confirm_ack(): valida que el aviso existe en el tenant, luego upsert_ack.

NO accede directamente a la DB — siempre vía repositorios.
NO contiene lógica de RBAC — eso es responsabilidad de los routers.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.core.dependencies import CurrentUser
from app.models.aviso import Aviso
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.aviso_repository import AvisoRepository
from app.schemas.aviso import (
    AvisoCreate,
    AvisoFeedItem,
    AvisoResponse,
    AvisoUpdate,
)


class AvisoService:
    def __init__(
        self,
        aviso_repo: AvisoRepository,
        asignacion_repo: AsignacionRepository,
    ) -> None:
        self.repo = aviso_repo
        self.asig_repo = asignacion_repo

    # ── CRUD de gestión ───────────────────────────────────────────────────────

    async def create_aviso(
        self,
        data: AvisoCreate,
        current_user: CurrentUser,
    ) -> AvisoResponse:
        """Crea un aviso. tenant_id tomado del JWT."""
        aviso = Aviso(
            tenant_id=current_user.tenant_id,
            alcance=data.alcance,
            materia_id=data.materia_id,
            cohorte_id=data.cohorte_id,
            rol_destino=data.rol_destino,
            severidad=data.severidad,
            titulo=data.titulo,
            cuerpo=data.cuerpo,
            inicio_en=data.inicio_en,
            fin_en=data.fin_en,
            orden=data.orden,
            activo=data.activo,
            requiere_ack=data.requiere_ack,
        )
        aviso = await self.repo.create(aviso)
        return await self._to_response(aviso)

    async def get_aviso(
        self,
        aviso_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> AvisoResponse:
        """Obtiene un aviso por ID. Lanza 404 si no existe."""
        aviso = await self.repo.get_by_id(aviso_id, current_user.tenant_id)
        if aviso is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aviso no encontrado",
            )
        return await self._to_response(aviso)

    async def list_avisos(
        self,
        current_user: CurrentUser,
    ) -> list[AvisoResponse]:
        """Lista todos los avisos del tenant (activos e inactivos)."""
        avisos = await self.repo.list_all(current_user.tenant_id)
        result = []
        for av in avisos:
            result.append(await self._to_response(av))
        return result

    async def update_aviso(
        self,
        aviso_id: uuid.UUID,
        data: AvisoUpdate,
        current_user: CurrentUser,
    ) -> AvisoResponse:
        """Actualiza campos de un aviso. Lanza 404 si no existe."""
        # Construir dict solo con campos provistos (excluir None)
        update_data = data.model_dump(exclude_none=True)
        aviso = await self.repo.update(aviso_id, current_user.tenant_id, update_data)
        if aviso is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aviso no encontrado",
            )
        return await self._to_response(aviso)

    async def delete_aviso(
        self,
        aviso_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> None:
        """Soft-delete un aviso. Lanza 404 si no existe."""
        deleted = await self.repo.soft_delete(aviso_id, current_user.tenant_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aviso no encontrado",
            )

    # ── Feed del destinatario ─────────────────────────────────────────────────

    async def get_mis_avisos(
        self,
        current_user: CurrentUser,
    ) -> list[AvisoFeedItem]:
        """Retorna el feed de avisos del usuario autenticado.

        Resuelve asignaciones vigentes del usuario para obtener
        materias_ids y cohortes_ids, luego delega al repositorio.
        El rol se extrae de current_user.roles (primer rol del JWT).
        """
        # Resolver asignaciones activas del usuario (vigentes hoy)
        asignaciones = await self.asig_repo.list_vigentes(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )

        today = date.today()
        materias_ids: list[uuid.UUID] = []
        cohortes_ids: list[uuid.UUID] = []

        for asig in asignaciones:
            # Filtrar solo vigentes (desde <= hoy <= hasta o hasta IS NULL)
            if asig.desde > today:
                continue
            if asig.hasta is not None and asig.hasta < today:
                continue
            if asig.materia_id is not None:
                materias_ids.append(asig.materia_id)
            if asig.cohorte_id is not None:
                cohortes_ids.append(asig.cohorte_id)

        # Obtener el rol principal del usuario (primer rol del JWT)
        rol_usuario = current_user.roles[0] if current_user.roles else ""

        avisos = await self.repo.get_feed(
            tenant_id=current_user.tenant_id,
            rol_usuario=rol_usuario,
            materias_ids=materias_ids,
            cohortes_ids=cohortes_ids,
            usuario_id=current_user.id,
        )

        # Construir feed items con ya_confirmado
        items = []
        for aviso in avisos:
            ya_confirmado = await self.repo.is_acked_by(aviso.id, current_user.id)
            items.append(
                AvisoFeedItem(
                    id=aviso.id,
                    alcance=aviso.alcance,
                    severidad=aviso.severidad,
                    titulo=aviso.titulo,
                    cuerpo=aviso.cuerpo,
                    inicio_en=aviso.inicio_en,
                    fin_en=aviso.fin_en,
                    orden=aviso.orden,
                    requiere_ack=aviso.requiere_ack,
                    ya_confirmado=ya_confirmado,
                )
            )
        return items

    # ── Acknowledgment ────────────────────────────────────────────────────────

    async def confirm_ack(
        self,
        aviso_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> None:
        """Confirma lectura de un aviso (idempotente).

        Valida que el aviso existe en el tenant antes del upsert.
        """
        aviso = await self.repo.get_by_id(aviso_id, current_user.tenant_id)
        if aviso is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aviso no encontrado",
            )
        await self.repo.upsert_ack(aviso_id, current_user.id)

    # ── Helpers privados ──────────────────────────────────────────────────────

    async def _to_response(self, aviso: Aviso) -> AvisoResponse:
        """Construye AvisoResponse con contadores derivados."""
        total_acks = await self.repo.count_acks(aviso.id)
        return AvisoResponse(
            id=aviso.id,
            tenant_id=aviso.tenant_id,
            alcance=aviso.alcance,
            materia_id=aviso.materia_id,
            cohorte_id=aviso.cohorte_id,
            rol_destino=aviso.rol_destino,
            severidad=aviso.severidad,
            titulo=aviso.titulo,
            cuerpo=aviso.cuerpo,
            inicio_en=aviso.inicio_en,
            fin_en=aviso.fin_en,
            orden=aviso.orden,
            activo=aviso.activo,
            requiere_ack=aviso.requiere_ack,
            total_vistas=total_acks,  # en este modelo, vista == ack (D3)
            total_acks=total_acks,
        )
