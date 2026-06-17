import uuid
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from fastapi import Request
    from app.core.dependencies import CurrentUser

# ── Catálogo de códigos de acción ─────────────────────────────────────────────

CALIFICACIONES_IMPORTAR = "CALIFICACIONES_IMPORTAR"
PADRON_CARGAR = "PADRON_CARGAR"  # Legacy — preferir PADRON_IMPORTADO
PADRON_IMPORTADO = "PADRON_IMPORTADO"
PADRON_VACIADO = "PADRON_VACIADO"
COMUNICACION_ENVIAR = "COMUNICACION_ENVIAR"
ASIGNACION_MODIFICAR = "ASIGNACION_MODIFICAR"
LIQUIDACION_CERRAR = "LIQUIDACION_CERRAR"
IMPERSONACION_INICIAR = "IMPERSONACION_INICIAR"
IMPERSONACION_FINALIZAR = "IMPERSONACION_FINALIZAR"


def record_audit_sync(
    session: Session,
    current_user: "CurrentUser",
    action: str,
    request: "Request | None" = None,
    detail: dict | None = None,
    rows_affected: int | None = None,
    materia_id: uuid.UUID | None = None,
) -> None:
    """Write an audit log entry using a synchronous SQLAlchemy session."""
    from app.models.audit_log import AuditLog

    ip: str | None = None
    user_agent: str | None = None
    if request is not None:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    entry = AuditLog(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        impersonado_id=current_user.impersonado_id,
        materia_id=materia_id,
        accion=action,
        detalle=detail,
        filas_afectadas=rows_affected,
        ip=ip,
        user_agent=user_agent,
    )
    session.add(entry)
    session.flush()


async def record_audit(
    session: AsyncSession,
    current_user: "CurrentUser",
    action: str,
    request: "Request | None" = None,
    detail: dict | None = None,
    rows_affected: int | None = None,
    materia_id: uuid.UUID | None = None,
) -> None:
    """Write an audit log entry using an async SQLAlchemy session."""
    from app.models.audit_log import AuditLog

    ip: str | None = None
    user_agent: str | None = None
    if request is not None:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    entry = AuditLog(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        impersonado_id=current_user.impersonado_id,
        materia_id=materia_id,
        accion=action,
        detalle=detail,
        filas_afectadas=rows_affected,
        ip=ip,
        user_agent=user_agent,
    )
    session.add(entry)
    await session.flush()
