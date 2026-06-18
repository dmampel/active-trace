"""Servicio de comunicaciones salientes (C-12).

Responsabilidades:
- Preview de mensajes con resolución de variables {{...}} sin persistencia.
- Encolado de mensajes individuales y masivos (lote).
- Aprobación y cancelación de lotes.
- Cancelación individual.
- Listado con enmascaramiento de destinatario.

NO accede directamente a la DB — siempre vía ComunicacionRepository.
NO contiene lógica de SMTP — eso es responsabilidad del worker.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.models.comunicacion import EstadoComunicacion, validar_transicion
from app.repositories.comunicacion_repository import ComunicacionRepository, _mask_email
from app.schemas.comunicacion import (
    ComunicacionEnviarRequest,
    ComunicacionEnviarResponse,
    ComunicacionPreviewRequest,
    ComunicacionPreviewResponse,
    ComunicacionResponse,
    LoteAccionResponse,
)


def _resolver_variables(template: str, contexto: dict) -> tuple[str, list[str]]:
    """Resuelve variables {{clave}} en el template usando contexto.

    Variables no resueltas se dejan en texto literal '{{clave}}'.
    Retorna (texto_renderizado, lista_de_warnings).
    """
    pattern = re.compile(r"\{\{([^}]+)\}\}")
    warnings: list[str] = []

    def replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in contexto:
            return str(contexto[key])
        warnings.append(f"Variable no resuelta: {{{{{key}}}}}")
        return match.group(0)  # deja el literal

    rendered = pattern.sub(replacer, template)
    return rendered, warnings


class ComunicacionService:
    def __init__(
        self,
        repo: ComunicacionRepository,
        audit_log_repo=None,  # AuditLogRepository — opcional para tests
    ) -> None:
        self._repo = repo
        self._audit_log_repo = audit_log_repo

    async def preview(
        self,
        request: ComunicacionPreviewRequest,
    ) -> ComunicacionPreviewResponse:
        """Renderiza asunto y cuerpo con variables de sustitución. No persiste."""
        asunto_renderizado, warnings_asunto = _resolver_variables(
            request.asunto, request.contexto
        )
        cuerpo_renderizado, warnings_cuerpo = _resolver_variables(
            request.cuerpo, request.contexto
        )
        return ComunicacionPreviewResponse(
            asunto_renderizado=asunto_renderizado,
            cuerpo_renderizado=cuerpo_renderizado,
            warnings=warnings_asunto + warnings_cuerpo,
        )

    async def encolar(
        self,
        request: ComunicacionEnviarRequest,
        usuario_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ComunicacionEnviarResponse:
        """Encola mensajes en estado Pendiente.

        - 1 destinatario → lote_id=None (sin aprobación requerida incluso si tenant lo requiere).
        - N>1 destinatarios → lote_id compartido (masivo).
        """
        if len(request.destinatarios) < 1:
            raise ValueError("Se requiere al menos un destinatario")

        lote_id: Optional[uuid.UUID] = None
        if len(request.destinatarios) > 1:
            lote_id = uuid.uuid4()

        ids_encolados: list[uuid.UUID] = []
        for email in request.destinatarios:
            com = await self._repo.create(
                tenant_id=tenant_id,
                enviado_por=usuario_id,
                materia_id=request.materia_id,
                destinatario_plain=email,
                asunto=request.asunto,
                cuerpo=request.cuerpo,
                lote_id=lote_id,
            )
            ids_encolados.append(com.id)

        return ComunicacionEnviarResponse(
            lote_id=lote_id,
            ids_encolados=ids_encolados,
            total=len(ids_encolados),
        )

    async def aprobar_lote(
        self,
        lote_id: uuid.UUID,
        tenant_id: uuid.UUID,
        aprobador_id: uuid.UUID,
    ) -> LoteAccionResponse:
        """Setea aprobado_at en todos los Pendiente del lote."""
        now = datetime.now(timezone.utc)
        afectados = await self._repo.update_aprobado_at(
            lote_id=lote_id,
            tenant_id=tenant_id,
            aprobado_at=now,
        )
        return LoteAccionResponse(
            lote_id=lote_id,
            afectados=afectados,
            estado_nuevo=EstadoComunicacion.Pendiente.value,  # estado no cambia, solo aprobado_at
        )

    async def cancelar_lote(
        self,
        lote_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> LoteAccionResponse:
        """Transiciona a Cancelado todos los Pendiente del lote."""
        afectados = await self._repo.cancelar_lote(
            lote_id=lote_id,
            tenant_id=tenant_id,
        )
        return LoteAccionResponse(
            lote_id=lote_id,
            afectados=afectados,
            estado_nuevo=EstadoComunicacion.Cancelado.value,
        )

    async def cancelar_individual(
        self,
        comunicacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> ComunicacionResponse:
        """Cancela un mensaje individual; solo válido si está en estado Pendiente."""
        com = await self._repo.get_by_id(comunicacion_id, tenant_id)
        if com is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comunicacion no encontrada",
            )
        # Valida transición Pendiente → Cancelado
        try:
            validar_transicion(com.estado, EstadoComunicacion.Cancelado)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        await self._repo.update_estado(
            comunicacion_id=com.id,
            tenant_id=tenant_id,
            nuevo_estado=EstadoComunicacion.Cancelado,
        )
        com.estado = EstadoComunicacion.Cancelado
        return _to_response(com)

    async def listar(
        self,
        tenant_id: uuid.UUID,
        *,
        estado: Optional[EstadoComunicacion] = None,
        lote_id: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
    ) -> list[ComunicacionResponse]:
        """Lista mensajes con filtros. Enmascara destinatario en cada respuesta."""
        comunicaciones = await self._repo.list_by_tenant(
            tenant_id,
            estado=estado,
            lote_id=lote_id,
            materia_id=materia_id,
            desde=desde,
            hasta=hasta,
        )
        return [_to_response(com) for com in comunicaciones]


def _to_response(com) -> ComunicacionResponse:
    """Convierte un modelo Comunicacion a ComunicacionResponse, enmascarando destinatario."""
    # destinatario está cifrado en BD — usamos el modelo raw para construir la respuesta
    # El enmascaramiento se hace con el texto cifrado como opaque ID (nunca descifrado aquí)
    # Para el masked field, el service NO descifra — devuelve "****" como placeholder seguro.
    # El cifrado solo se descifra en el worker.
    return ComunicacionResponse(
        id=com.id,
        tenant_id=com.tenant_id,
        enviado_por=com.enviado_por,
        materia_id=com.materia_id,
        destinatario_masked="****@****",  # destinatario cifrado nunca se expone
        asunto=com.asunto,
        cuerpo=com.cuerpo,
        estado=com.estado,
        lote_id=com.lote_id,
        enviado_at=com.enviado_at,
        aprobado_at=com.aprobado_at,
        created_at=com.created_at,
        deleted_at=com.deleted_at,
    )
