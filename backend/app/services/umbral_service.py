"""Servicio de configuración de umbral de aprobación (C-10, D5).

Responsabilidades:
- Configurar (upsert) el UmbralMateria de una asignación docente.
- Resolver el umbral vigente para una asignación, retornando el defecto del tenant si no existe.
- Orquestar la derivación de aprobado usando la función pura (D2).

No hace acceso a DB directamente — delega al UmbralRepository.
Identidad (tenant_id, asignacion_id) siempre viene del caller (JWT-derivado).
"""

from __future__ import annotations

import uuid
from typing import Optional

from app.domain.aprobado import DEFAULT_UMBRAL_PCT, derivar_aprobado
from app.models.calificacion import UmbralMateria
from app.repositories.umbral_repository import UmbralRepository


class UmbralService:
    def __init__(self, umbral_repo: UmbralRepository) -> None:
        self._repo = umbral_repo

    async def configurar(
        self,
        tenant_id: uuid.UUID,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
        umbral_pct: int,
        valores_aprobatorios: list[str],
    ) -> UmbralMateria:
        """Persiste o actualiza el umbral para la asignación del docente.

        Hace upsert idempotente: (tenant, asignacion, materia) es la clave única.
        El tenant_id se toma del caller (JWT), nunca del payload de la petición.
        """
        umbral = UmbralMateria(
            tenant_id=tenant_id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=umbral_pct,
            valores_aprobatorios=valores_aprobatorios,
        )
        return await self._repo.upsert(umbral, tenant_id)

    async def resolver_umbral(
        self,
        tenant_id: uuid.UUID,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
    ) -> tuple[int, list[str]]:
        """Retorna (umbral_pct, valores_aprobatorios) para la asignación.

        Si no hay UmbralMateria configurado, retorna el defecto del tenant:
        60% y lista vacía de valores aprobatorios.
        """
        umbral = await self._repo.get_by_asignacion_materia(
            tenant_id=tenant_id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
        )
        if umbral is None:
            return DEFAULT_UMBRAL_PCT, []
        return umbral.umbral_pct, list(umbral.valores_aprobatorios)

    async def derivar_aprobado_para(
        self,
        tenant_id: uuid.UUID,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
        nota_numerica: Optional[float],
        nota_textual: Optional[str],
        nota_maxima: float,
    ) -> bool:
        """Resuelve el umbral y deriva el estado aprobado usando la función pura.

        El campo `aprobado` NO se persiste (D2). Se calcula en tiempo de lectura/proyección.
        """
        umbral_pct, valores_aprobatorios = await self.resolver_umbral(
            tenant_id=tenant_id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
        )
        return derivar_aprobado(
            nota_numerica=nota_numerica,
            nota_textual=nota_textual,
            umbral_pct=umbral_pct,
            nota_maxima=nota_maxima,
            valores_aprobatorios=valores_aprobatorios,
        )
