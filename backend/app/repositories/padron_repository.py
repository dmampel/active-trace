"""Repositorio para VersionPadron y EntradaPadron.

Responsabilidades:
- Todas las queries son tenant-scoped por defecto.
- activar_version / crear_version_con_entradas garantizan la invariante de
  que solo puede existir una versión activa por (tenant, materia, cohorte).
- El cifrado/descifrado de email_enc NO ocurre aquí — es responsabilidad del Service.
"""

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.padron import EntradaPadron, VersionPadron


class PadronRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_activa(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[VersionPadron]:
        """Retorna la VersionPadron activa para (materia, cohorte, tenant) o None."""
        q = select(VersionPadron).where(
            VersionPadron.tenant_id == tenant_id,
            VersionPadron.materia_id == materia_id,
            VersionPadron.cohorte_id == cohorte_id,
            VersionPadron.activa.is_(True),
            VersionPadron.deleted_at.is_(None),
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def listar_versiones(
        self,
        materia_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[VersionPadron]:
        """Lista todas las versiones (activas e inactivas) de una materia, ordenadas por cargado_at desc."""
        q = (
            select(VersionPadron)
            .where(
                VersionPadron.tenant_id == tenant_id,
                VersionPadron.materia_id == materia_id,
                VersionPadron.deleted_at.is_(None),
            )
            .order_by(VersionPadron.cargado_at.desc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_entradas(
        self,
        version_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[EntradaPadron]:
        """Lista las entradas de una versión, verificando tenant para seguridad."""
        q = select(EntradaPadron).where(
            EntradaPadron.version_id == version_id,
            EntradaPadron.tenant_id == tenant_id,
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def crear_version_con_entradas(
        self,
        version: VersionPadron,
        entradas: list[EntradaPadron],
    ) -> VersionPadron:
        """Persiste una nueva versión y sus entradas en una transacción atómica.

        Si ya existe una versión activa para el mismo (tenant, materia, cohorte),
        la desactiva antes de guardar la nueva. Garantiza que solo haya una activa.
        """
        # Desactivar versión anterior si existe
        await self.session.execute(
            update(VersionPadron)
            .where(
                VersionPadron.tenant_id == version.tenant_id,
                VersionPadron.materia_id == version.materia_id,
                VersionPadron.cohorte_id == version.cohorte_id,
                VersionPadron.activa.is_(True),
                VersionPadron.deleted_at.is_(None),
            )
            .values(activa=False)
        )

        # Persistir nueva versión
        self.session.add(version)
        await self.session.flush()  # obtener version.id antes de usarlo en entradas

        # Asignar FK de versión a cada entrada y persistir
        for entrada in entradas:
            entrada.version_id = version.id
            self.session.add(entrada)

        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def soft_delete_activa(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        tenant_id: uuid.UUID,
        cargado_por: uuid.UUID,
    ) -> Optional[VersionPadron]:
        """Soft-delete de la versión activa si fue cargada por el usuario indicado.

        Retorna la versión soft-deleted, o None si no existe o no es del usuario.
        """
        version = await self.get_activa(materia_id, cohorte_id, tenant_id)
        if version is None:
            return None
        if version.cargado_por != cargado_por:
            return None  # el caller debe elevar 403

        from datetime import datetime, timezone
        await self.session.execute(
            update(VersionPadron)
            .where(VersionPadron.id == version.id)
            .values(deleted_at=datetime.now(timezone.utc), activa=False)
        )
        await self.session.commit()
        await self.session.refresh(version)
        return version
