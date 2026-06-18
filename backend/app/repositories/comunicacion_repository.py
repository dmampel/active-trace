"""Repositorio para Comunicacion (C-12).

Responsabilidades:
- Todas las queries son tenant-scoped por defecto (tenant_id como primer argumento).
- Sin lógica de negocio (ni máquina de estados, ni cifrado, ni auditoría).
- Cifrado: `destinatario` se cifra en create() usando el cipher pasado como parámetro;
  se descifra solo en get_pendientes_para_worker() donde el worker lo necesita.
- Soft delete: las queries de listado excluyen filas con deleted_at no nulo.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.models.tenant import Tenant


def _mask_email(email: str) -> str:
    """Enmascara un email: 'alumno@dominio.com' → 'a****@dominio.com'."""
    if "@" not in email:
        return "****"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"{local}****@{domain}"
    return f"{local[0]}{'*' * (len(local) - 1)}@{domain}"


class ComunicacionRepository:
    def __init__(self, session: AsyncSession, cipher) -> None:
        """
        Args:
            session: sesión async SQLAlchemy.
            cipher: instancia de AES256GCMCipher para cifrar/descifrar destinatario.
        """
        self.session = session
        self._cipher = cipher

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        enviado_por: uuid.UUID,
        materia_id: uuid.UUID,
        destinatario_plain: str,
        asunto: str,
        cuerpo: str,
        lote_id: Optional[uuid.UUID] = None,
    ) -> Comunicacion:
        """Persiste un mensaje en estado Pendiente con destinatario cifrado."""
        destinatario_enc = self._cipher.encrypt(destinatario_plain)
        com = Comunicacion(
            tenant_id=tenant_id,
            enviado_por=enviado_por,
            materia_id=materia_id,
            destinatario=destinatario_enc,
            asunto=asunto,
            cuerpo=cuerpo,
            estado=EstadoComunicacion.Pendiente,
            lote_id=lote_id,
        )
        self.session.add(com)
        await self.session.flush()
        await self.session.refresh(com)
        return com

    async def get_by_id(
        self,
        comunicacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[Comunicacion]:
        """Obtiene un mensaje por ID dentro del tenant, excluyendo soft-deleted."""
        q = select(Comunicacion).where(
            Comunicacion.id == comunicacion_id,
            Comunicacion.tenant_id == tenant_id,
            Comunicacion.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        estado: Optional[EstadoComunicacion] = None,
        lote_id: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
    ) -> list[Comunicacion]:
        """Lista mensajes de un tenant con filtros opcionales, excluyendo soft-deleted."""
        conditions = [
            Comunicacion.tenant_id == tenant_id,
            Comunicacion.deleted_at.is_(None),
        ]
        if estado is not None:
            conditions.append(Comunicacion.estado == estado)
        if lote_id is not None:
            conditions.append(Comunicacion.lote_id == lote_id)
        if materia_id is not None:
            conditions.append(Comunicacion.materia_id == materia_id)
        if desde is not None:
            conditions.append(Comunicacion.created_at >= desde)
        if hasta is not None:
            conditions.append(Comunicacion.created_at <= hasta)

        q = select(Comunicacion).where(and_(*conditions)).order_by(
            Comunicacion.created_at.desc()
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def update_estado(
        self,
        comunicacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
        nuevo_estado: EstadoComunicacion,
        *,
        enviado_at: Optional[datetime] = None,
    ) -> Optional[Comunicacion]:
        """Actualiza el estado de un mensaje; opcionalmente fija enviado_at."""
        values: dict = {"estado": nuevo_estado}
        if enviado_at is not None:
            values["enviado_at"] = enviado_at

        q = (
            update(Comunicacion)
            .where(
                Comunicacion.id == comunicacion_id,
                Comunicacion.tenant_id == tenant_id,
            )
            .values(**values)
            .returning(Comunicacion)
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def update_aprobado_at(
        self,
        lote_id: uuid.UUID,
        tenant_id: uuid.UUID,
        aprobado_at: datetime,
    ) -> int:
        """Setea aprobado_at en todos los Pendiente del lote. Retorna filas afectadas."""
        q = (
            update(Comunicacion)
            .where(
                Comunicacion.lote_id == lote_id,
                Comunicacion.tenant_id == tenant_id,
                Comunicacion.estado == EstadoComunicacion.Pendiente,
                Comunicacion.deleted_at.is_(None),
            )
            .values(aprobado_at=aprobado_at)
        )
        result = await self.session.execute(q)
        return result.rowcount

    async def cancelar_lote(
        self,
        lote_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> int:
        """Transiciona a Cancelado todos los Pendiente del lote. Retorna filas afectadas."""
        q = (
            update(Comunicacion)
            .where(
                Comunicacion.lote_id == lote_id,
                Comunicacion.tenant_id == tenant_id,
                Comunicacion.estado == EstadoComunicacion.Pendiente,
                Comunicacion.deleted_at.is_(None),
            )
            .values(estado=EstadoComunicacion.Cancelado)
        )
        result = await self.session.execute(q)
        return result.rowcount

    async def get_pendientes_para_worker(
        self,
        tenant_id: uuid.UUID,
        requiere_aprobacion: bool,
    ) -> list[tuple[Comunicacion, str]]:
        """Obtiene mensajes Pendiente elegibles para despacho.

        Si requiere_aprobacion=True, solo devuelve los que tienen aprobado_at IS NOT NULL.
        Si requiere_aprobacion=False, devuelve todos los Pendiente.

        Retorna lista de (Comunicacion, destinatario_descifrado).
        """
        conditions = [
            Comunicacion.tenant_id == tenant_id,
            Comunicacion.estado == EstadoComunicacion.Pendiente,
            Comunicacion.deleted_at.is_(None),
        ]
        if requiere_aprobacion:
            conditions.append(Comunicacion.aprobado_at.is_not(None))

        q = select(Comunicacion).where(and_(*conditions)).order_by(
            Comunicacion.created_at.asc()
        )
        result = await self.session.execute(q)
        comunicaciones = list(result.scalars().all())
        return [
            (com, self._cipher.decrypt(com.destinatario))
            for com in comunicaciones
        ]

    async def get_pendientes_para_worker_sin_tenant(
        self,
    ) -> list[tuple[Comunicacion, str, bool]]:
        """Obtiene mensajes Pendiente elegibles para despacho de TODOS los tenants.

        Hace JOIN con tenant para obtener requiere_aprobacion.
        Retorna lista de (Comunicacion, destinatario_descifrado, requiere_aprobacion).
        """
        q = (
            select(Comunicacion, Tenant.requiere_aprobacion)
            .join(Tenant, Comunicacion.tenant_id == Tenant.id)
            .where(
                Comunicacion.estado == EstadoComunicacion.Pendiente,
                Comunicacion.deleted_at.is_(None),
                Tenant.deleted_at.is_(None),
            )
            .order_by(Comunicacion.created_at.asc())
        )
        result = await self.session.execute(q)
        rows = result.all()

        out = []
        for com, req_aprobacion in rows:
            if req_aprobacion and com.aprobado_at is None:
                continue  # no elegible
            out.append((com, self._cipher.decrypt(com.destinatario), req_aprobacion))
        return out

    async def reset_enviando_huerfanos(self) -> int:
        """Resetea a Error todos los mensajes Enviando con enviado_at IS NULL y antiguos.

        Se llama al arrancar el worker para limpiar mensajes que quedaron colgados
        por un reinicio de la app mientras estaban siendo despachados.
        Umbral: 5 minutos desde created_at.
        Retorna número de filas afectadas.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        q = (
            update(Comunicacion)
            .where(
                Comunicacion.estado == EstadoComunicacion.Enviando,
                Comunicacion.enviado_at.is_(None),
                Comunicacion.created_at < cutoff,
            )
            .values(estado=EstadoComunicacion.Error)
        )
        result = await self.session.execute(q)
        return result.rowcount
