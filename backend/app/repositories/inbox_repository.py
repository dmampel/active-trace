"""Repositorio de mensajería interna (C-20).

Reglas:
- Toda query filtra por tenant_id por defecto (row-level isolation).
- Soft delete respetado: excluye registros con deleted_at no nulo.
- Filtro adicional por participación del usuario (autor_id o destinatario_id).
- Acceso a hilo ajeno: retorna None (el service convierte a 404).
- NO acoplado a ComunicacionDocente (C-12).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mensajeria import HiloMensaje, MensajeInterno


class InboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def listar_hilos_recibidos(
        self, tenant_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> list[HiloMensaje]:
        """Lista hilos donde el usuario es destinatario de al menos un mensaje.

        Filtra por tenant_id y excluye hilos con deleted_at.
        Solo retorna hilos donde el usuario participa como destinatario.
        """
        # Subquery: hilos donde usuario es destinatario
        sub = (
            select(MensajeInterno.hilo_id)
            .where(
                MensajeInterno.tenant_id == tenant_id,
                MensajeInterno.destinatario_id == usuario_id,
                MensajeInterno.deleted_at.is_(None),
            )
            .distinct()
        )
        q = select(HiloMensaje).where(
            HiloMensaje.tenant_id == tenant_id,
            HiloMensaje.deleted_at.is_(None),
            HiloMensaje.id.in_(sub),
        ).order_by(HiloMensaje.created_at.desc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_hilo_para_participante(
        self,
        hilo_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> Optional[HiloMensaje]:
        """Retorna un hilo solo si el usuario participa (como creador o destinatario).

        Retorna None si el hilo no existe, es de otro tenant, fue eliminado
        o el usuario no es participante. El service convierte None → 404.
        """
        # Verificar que el usuario es participante (creador o destinatario de algún mensaje)
        hilo_q = select(HiloMensaje).where(
            HiloMensaje.id == hilo_id,
            HiloMensaje.tenant_id == tenant_id,
            HiloMensaje.deleted_at.is_(None),
        )
        result = await self.session.execute(hilo_q)
        hilo = result.scalar_one_or_none()
        if hilo is None:
            return None

        # Verificar participación
        participante_q = select(MensajeInterno.id).where(
            MensajeInterno.hilo_id == hilo_id,
            MensajeInterno.tenant_id == tenant_id,
            MensajeInterno.deleted_at.is_(None),
            or_(
                MensajeInterno.autor_id == usuario_id,
                MensajeInterno.destinatario_id == usuario_id,
            ),
        ).limit(1)
        part_result = await self.session.execute(participante_q)
        if part_result.scalar_one_or_none() is None:
            return None

        return hilo

    async def listar_mensajes_hilo(
        self,
        hilo_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[MensajeInterno]:
        """Lista mensajes de un hilo ordenados cronológicamente (excluyendo eliminados)."""
        q = select(MensajeInterno).where(
            MensajeInterno.hilo_id == hilo_id,
            MensajeInterno.tenant_id == tenant_id,
            MensajeInterno.deleted_at.is_(None),
        ).order_by(MensajeInterno.created_at.asc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def marcar_mensajes_leidos(
        self,
        hilo_id: uuid.UUID,
        tenant_id: uuid.UUID,
        destinatario_id: uuid.UUID,
    ) -> None:
        """Marca como leídos los mensajes dirigidos al usuario en el hilo."""
        q = select(MensajeInterno).where(
            MensajeInterno.hilo_id == hilo_id,
            MensajeInterno.tenant_id == tenant_id,
            MensajeInterno.destinatario_id == destinatario_id,
            MensajeInterno.leido.is_(False),
            MensajeInterno.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        mensajes = result.scalars().all()
        for m in mensajes:
            m.leido = True
        await self.session.commit()

    async def crear_hilo_con_mensaje(
        self,
        tenant_id: uuid.UUID,
        creado_por: uuid.UUID,
        asunto: str,
        destinatario_id: uuid.UUID,
        cuerpo: str,
    ) -> HiloMensaje:
        """Crea un hilo nuevo con su primer mensaje. Retorna el hilo creado."""
        hilo = HiloMensaje(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            asunto=asunto,
            creado_por=creado_por,
        )
        self.session.add(hilo)
        await self.session.flush()  # Para obtener hilo.id antes del commit

        mensaje = MensajeInterno(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            hilo_id=hilo.id,
            autor_id=creado_por,
            destinatario_id=destinatario_id,
            cuerpo=cuerpo,
            leido=False,
        )
        self.session.add(mensaje)
        await self.session.commit()
        await self.session.refresh(hilo)
        return hilo

    async def agregar_mensaje(
        self,
        hilo_id: uuid.UUID,
        tenant_id: uuid.UUID,
        autor_id: uuid.UUID,
        destinatario_id: uuid.UUID,
        cuerpo: str,
    ) -> MensajeInterno:
        """Agrega un mensaje de respuesta a un hilo existente."""
        mensaje = MensajeInterno(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            hilo_id=hilo_id,
            autor_id=autor_id,
            destinatario_id=destinatario_id,
            cuerpo=cuerpo,
            leido=False,
        )
        self.session.add(mensaje)
        await self.session.commit()
        await self.session.refresh(mensaje)
        return mensaje
