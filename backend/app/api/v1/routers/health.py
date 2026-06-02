"""Router de health-check — única ruta de C-01.

GET /health reporta:
- liveness: la app está corriendo
- readiness: la DB es alcanzable (degradado = down, no crash)
"""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Respuesta del endpoint de salud."""

    status: str
    database: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Estado de salud de la aplicación",
    description=(
        "Reporta liveness (la app está corriendo) y readiness de la base de datos. "
        "Si la DB no es alcanzable, el campo database vale 'down' pero el proceso no se cae."
    ),
)
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Verifica liveness + readiness de la base de datos."""
    db_status = "up"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health-check: DB no alcanzable — %s", exc)
        db_status = "down"

    return JSONResponse(
        content={"status": "ok", "database": db_status},
        status_code=200,
    )
