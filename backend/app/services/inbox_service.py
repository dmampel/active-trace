"""Service de mensajería interna (C-20).

Responsabilidades:
- Identidad SIEMPRE del JWT (current_user.id / tenant_id).
- Listar hilos donde el usuario del JWT es destinatario.
- Leer un hilo y marcar como leídos los mensajes dirigidos al usuario.
- Responder en un hilo existente (autor_id del JWT).
- Crear un hilo nuevo hacia un destinatario del mismo tenant.
- Acceso a hilo ajeno → 404 (no filtra existencia).
- Destinatario de otro tenant → 404.
- Sin cola/worker: inbox es puramente in-app.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


class InboxService:
    def __init__(self, session: AsyncSession, current_user):
        self.session = session
        self.current_user = current_user

    def _repo(self):
        from app.repositories.inbox_repository import InboxRepository
        return InboxRepository(self.session)

    def _usuario_repo(self):
        from app.repositories.usuario_repository import UsuarioRepository
        return UsuarioRepository(self.session)

    def _hilo_to_dto(self, hilo):
        from app.schemas.mensajeria import HiloRead
        return HiloRead(
            id=hilo.id,
            tenant_id=hilo.tenant_id,
            asunto=hilo.asunto,
            creado_por=hilo.creado_por,
            created_at=hilo.created_at,
        )

    def _mensaje_to_dto(self, mensaje):
        from app.schemas.mensajeria import MensajeRead
        return MensajeRead(
            id=mensaje.id,
            hilo_id=mensaje.hilo_id,
            autor_id=mensaje.autor_id,
            destinatario_id=mensaje.destinatario_id,
            cuerpo=mensaje.cuerpo,
            leido=mensaje.leido,
            created_at=mensaje.created_at,
        )

    async def listar_inbox(self):
        """Lista hilos donde el usuario del JWT es destinatario."""
        hilos = await self._repo().listar_hilos_recibidos(
            self.current_user.tenant_id, self.current_user.id
        )
        return [self._hilo_to_dto(h) for h in hilos]

    async def leer_hilo(self, hilo_id: uuid.UUID):
        """Retorna un hilo con sus mensajes ordenados y marca los del usuario como leídos.

        Si el usuario no participa o el hilo es de otro tenant → 404.
        """
        hilo = await self._repo().get_hilo_para_participante(
            hilo_id, self.current_user.tenant_id, self.current_user.id
        )
        if hilo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hilo no encontrado",
            )

        # Marcar como leídos los mensajes dirigidos al usuario
        await self._repo().marcar_mensajes_leidos(
            hilo_id, self.current_user.tenant_id, self.current_user.id
        )

        mensajes = await self._repo().listar_mensajes_hilo(
            hilo_id, self.current_user.tenant_id
        )

        from app.schemas.mensajeria import HiloConMensajesRead
        return HiloConMensajesRead(
            hilo=self._hilo_to_dto(hilo),
            mensajes=[self._mensaje_to_dto(m) for m in mensajes],
        )

    async def responder_hilo(self, hilo_id: uuid.UUID, cuerpo: str):
        """Agrega un mensaje de respuesta al hilo.

        El autor_id es el usuario del JWT. El destinatario es el otro participante.
        Si el usuario no participa → 404.
        """
        hilo = await self._repo().get_hilo_para_participante(
            hilo_id, self.current_user.tenant_id, self.current_user.id
        )
        if hilo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hilo no encontrado",
            )

        # El destinatario es el creador del hilo si quien responde es distinto,
        # o se determina por el último mensaje (patrón de dos participantes).
        # Simplificación: el destinatario es el creado_por si el respondedor es distinto.
        if hilo.creado_por == self.current_user.id:
            # El creador responde → necesitamos al otro participante
            mensajes = await self._repo().listar_mensajes_hilo(
                hilo_id, self.current_user.tenant_id
            )
            # El destinatario es alguien distinto del creador
            destinatario_id = next(
                (m.destinatario_id for m in mensajes if m.destinatario_id != self.current_user.id),
                None,
            ) or next(
                (m.autor_id for m in mensajes if m.autor_id != self.current_user.id),
                hilo.creado_por,
            )
        else:
            # El destinatario del hilo responde → el destinatario es el creador
            destinatario_id = hilo.creado_por

        mensaje = await self._repo().agregar_mensaje(
            hilo_id=hilo_id,
            tenant_id=self.current_user.tenant_id,
            autor_id=self.current_user.id,
            destinatario_id=destinatario_id,
            cuerpo=cuerpo,
        )
        return self._mensaje_to_dto(mensaje)

    async def crear_hilo(
        self, destinatario_id: uuid.UUID, asunto: str, cuerpo: str
    ):
        """Crea un hilo nuevo con su primer mensaje.

        El destinatario debe ser un usuario activo del mismo tenant → 404 si no.
        """
        destinatario = await self._usuario_repo().get_by_id(
            destinatario_id, self.current_user.tenant_id
        )
        if destinatario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destinatario no encontrado en el tenant",
            )

        hilo = await self._repo().crear_hilo_con_mensaje(
            tenant_id=self.current_user.tenant_id,
            creado_por=self.current_user.id,
            asunto=asunto,
            destinatario_id=destinatario_id,
            cuerpo=cuerpo,
        )
        return self._hilo_to_dto(hilo)
