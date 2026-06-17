"""Servicio principal de calificaciones (C-10).

Orquesta:
1. preview(): llama al parser, retorna preview sin persistir. Sin auditoría.
2. importar(): construye Calificaciones desde parser + selección, hace bulk_crear,
               registra AuditLog solo si se persistieron filas (tarea 7.3).
3. cruzar_finalizacion(): cruza reporte de finalización con calificaciones importadas.

No contiene lógica de parsing ni de derivación de aprobado (delegadas a módulos puros).
Identidad (tenant_id, actor_id) SIEMPRE viene del caller (JWT) — nunca del payload.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.calificacion_repository import CalificacionRepository
from app.services.calificacion_finalizacion import detectar_sin_corregir
from app.services.calificacion_parser import construir_calificaciones, parsear_csv_preview
from app.services.umbral_service import UmbralService


class CalificacionService:
    def __init__(
        self,
        cal_repo: CalificacionRepository,
        audit_repo: AuditLogRepository,
        umbral_service: UmbralService,
    ) -> None:
        self._cal_repo = cal_repo
        self._audit_repo = audit_repo
        self._umbral_svc = umbral_service

    async def preview(
        self,
        tenant_id: uuid.UUID,
        materia_id: uuid.UUID,
        csv_data: bytes,
        escala_textual: list[str],
    ) -> dict:
        """Parsea el CSV y retorna la estructura de preview SIN persistir nada.

        No genera AuditLog (nada fue escrito).
        """
        return parsear_csv_preview(csv_data, escala_textual)

    async def importar(
        self,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        materia_id: uuid.UUID,
        actividades: list[dict],
        seleccionadas: list[str],
        filas: list[dict],
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        """Persiste las calificaciones para las actividades seleccionadas.

        Registra AuditLog SOLO si se persistieron calificaciones (filas > 0).
        Selección vacía → 0 calificaciones, sin auditoría.

        Returns:
            {"filas_afectadas": int, "calificaciones": [...]}
        """
        importado_at = datetime.now(timezone.utc)
        cals = construir_calificaciones(
            filas=filas,
            actividades=actividades,
            seleccionadas=seleccionadas,
            materia_id=materia_id,
            tenant_id=tenant_id,
            importado_at=importado_at,
        )

        if not cals:
            return {"filas_afectadas": 0, "calificaciones": []}

        count = await self._cal_repo.bulk_crear(cals)

        # Auditoría: solo si hubo persistencia efectiva
        await self._audit_repo.create_entry({
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "materia_id": materia_id,
            "accion": "CALIFICACIONES_IMPORTAR",
            "filas_afectadas": count,
            "ip": ip,
            "user_agent": user_agent,
            "detalle": {"actividades_importadas": seleccionadas},
        })
        await self._cal_repo.session.commit()

        return {"filas_afectadas": count, "calificaciones": cals}

    async def cruzar_finalizacion(
        self,
        tenant_id: uuid.UUID,
        materia_id: uuid.UUID,
        finalizaciones: list[dict],
    ) -> list[dict]:
        """Cruza el reporte de finalización con calificaciones importadas.

        Retorna lista de entregas textuales finalizadas sin calificación (RN-07/RN-08).
        """
        cals = await self._cal_repo.listar_por_materia(materia_id, tenant_id)
        return detectar_sin_corregir(finalizaciones, cals)
