"""Worker asíncrono de despacho de comunicaciones (C-12).

Responsabilidades:
- Al arrancar: resetear mensajes huérfanos en estado Enviando (crash recovery).
- Loop principal: SELECT Pendiente elegibles → UPDATE Enviando → SMTP → UPDATE Enviado/Error.
- Al enviar exitosamente: registrar audit log COMUNICACION_ENVIAR.
- Continúa con el siguiente mensaje aunque uno falle.

El worker se arranca como asyncio.create_task en el lifespan de FastAPI.
Puede detenerse mediante un asyncio.Event de cancelación.

Diseño:
- La resolución de "es elegible" considera tenant.requiere_aprobacion:
  - False → todos los Pendiente son elegibles.
  - True  → solo los Pendiente con aprobado_at IS NOT NULL.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def run_worker(
    db_session_factory: Any,
    smtp_client: Any,
    poll_interval: int = 10,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Loop principal del worker de comunicaciones.

    Args:
        db_session_factory: factory de sesiones async (async_sessionmaker).
        smtp_client: cliente SMTP con método async send(to, subject, body).
        poll_interval: segundos entre iteraciones del loop.
        stop_event: si se setea, el worker termina limpiamente.
    """
    logger.info("ComunicacionWorker: iniciando")

    # ── Startup: resetear mensajes Enviando huérfanos ─────────────────────────
    async with db_session_factory() as session:
        from app.repositories.comunicacion_repository import ComunicacionRepository
        from app.core.security import AES256GCMCipher, derive_encryption_key
        from app.core.config import get_settings

        settings = get_settings()
        cipher = AES256GCMCipher(derive_encryption_key(settings.encryption_key))
        repo = ComunicacionRepository(session, cipher)

        huerfanos = await repo.reset_enviando_huerfanos()
        if huerfanos > 0:
            logger.warning(
                "ComunicacionWorker: %d mensajes huérfanos (Enviando sin enviado_at) → Error",
                huerfanos,
            )
        await session.commit()

    # ── Loop principal ────────────────────────────────────────────────────────
    while True:
        if stop_event is not None and stop_event.is_set():
            logger.info("ComunicacionWorker: stop_event recibido, terminando")
            break

        try:
            await _process_pendientes(db_session_factory, smtp_client)
        except Exception as exc:  # noqa: BLE001
            logger.error("ComunicacionWorker: error en ciclo de procesamiento: %s", exc)

        try:
            if stop_event is not None:
                await asyncio.wait_for(stop_event.wait(), timeout=poll_interval)
                logger.info("ComunicacionWorker: stop_event recibido durante sleep")
                break
            else:
                await asyncio.sleep(poll_interval)
        except asyncio.TimeoutError:
            pass  # poll_interval expiró, continúa el loop


async def _process_pendientes(db_session_factory: Any, smtp_client: Any) -> None:
    """Procesa todos los mensajes Pendiente elegibles en una iteración."""
    from app.repositories.comunicacion_repository import ComunicacionRepository
    from app.repositories.audit_log_repository import AuditLogRepository
    from app.models.comunicacion import EstadoComunicacion
    from app.core.security import AES256GCMCipher, derive_encryption_key
    from app.core.config import get_settings

    settings = get_settings()
    cipher = AES256GCMCipher(derive_encryption_key(settings.encryption_key))

    async with db_session_factory() as session:
        repo = ComunicacionRepository(session, cipher)
        audit_repo = AuditLogRepository(session)

        # Obtener todos los pendientes elegibles (join con tenant para requiere_aprobacion)
        pendientes = await repo.get_pendientes_para_worker_sin_tenant()

        for com, destinatario_plain, _req_aprobacion in pendientes:
            await _despachar_mensaje(
                session=session,
                repo=repo,
                audit_repo=audit_repo,
                com=com,
                destinatario_plain=destinatario_plain,
                smtp_client=smtp_client,
            )

        await session.commit()


async def _despachar_mensaje(
    session: Any,
    repo: "ComunicacionRepository",
    audit_repo: "AuditLogRepository",
    com: Any,
    destinatario_plain: str,
    smtp_client: Any,
) -> None:
    """Intenta despachar un mensaje individual vía SMTP.

    Flujo:
    1. UPDATE estado=Enviando (optimistic lock)
    2. SMTP send
    3a. Éxito → UPDATE estado=Enviado, enviado_at=now, audit log
    3b. Fallo → UPDATE estado=Error
    """
    from app.models.comunicacion import EstadoComunicacion
    from app.repositories.audit_log_repository import AuditLogRepository

    # 1. Marcar Enviando
    await repo.update_estado(
        comunicacion_id=com.id,
        tenant_id=com.tenant_id,
        nuevo_estado=EstadoComunicacion.Enviando,
    )

    # 2. SMTP send
    try:
        await smtp_client.send(
            to=destinatario_plain,
            subject=com.asunto,
            body=com.cuerpo,
        )
        # 3a. Éxito
        now = datetime.now(timezone.utc)
        await repo.update_estado(
            comunicacion_id=com.id,
            tenant_id=com.tenant_id,
            nuevo_estado=EstadoComunicacion.Enviado,
            enviado_at=now,
        )

        # Audit log COMUNICACION_ENVIAR
        await audit_repo.create_entry(
            {
                "tenant_id": com.tenant_id,
                "actor_id": com.enviado_por,
                "accion": "COMUNICACION_ENVIAR",
                "detalle": {
                    "comunicacion_id": str(com.id),
                    "materia_id": str(com.materia_id),
                    "lote_id": str(com.lote_id) if com.lote_id else None,
                },
            }
        )
        logger.info(
            "ComunicacionWorker: enviado comunicacion_id=%s tenant=%s",
            com.id,
            com.tenant_id,
        )

    except Exception as exc:  # noqa: BLE001
        # 3b. Fallo
        logger.error(
            "ComunicacionWorker: SMTP falló para comunicacion_id=%s: %s",
            com.id,
            exc,
        )
        await repo.update_estado(
            comunicacion_id=com.id,
            tenant_id=com.tenant_id,
            nuevo_estado=EstadoComunicacion.Error,
        )
