"""Repositorio para TenantMoodleConfig.

Responsabilidades:
- get_by_tenant: obtener la configuración Moodle de un tenant
- upsert: crear o reemplazar la configuración (un tenant tiene máximo una)

El descifrado de moodle_url_enc y moodle_token_enc NO ocurre aquí — es
responsabilidad del Service.
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_moodle_config import TenantMoodleConfig


class MoodleConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_tenant(self, tenant_id: uuid.UUID) -> Optional[TenantMoodleConfig]:
        """Retorna la configuración Moodle del tenant, o None si no está configurada."""
        q = select(TenantMoodleConfig).where(
            TenantMoodleConfig.tenant_id == tenant_id
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        config: TenantMoodleConfig,
        tenant_id: uuid.UUID,
    ) -> TenantMoodleConfig:
        """Crea o reemplaza la configuración Moodle del tenant.

        Si ya existe una configuración para el tenant, la reemplaza.
        Garantiza que solo exista una fila por tenant.
        """
        existing = await self.get_by_tenant(tenant_id)
        if existing is not None:
            existing.moodle_url_enc = config.moodle_url_enc
            existing.moodle_token_enc = config.moodle_token_enc
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        config.tenant_id = tenant_id
        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)
        return config
