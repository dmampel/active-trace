"""Dependency injection de FastAPI para la sesión de base de datos.

get_db: async-generator que abre una sesión por request y la cierra en finally,
garantizando que no haya fugas de conexión al pool aunque el handler lance excepción.

Los slots get_current_user, get_tenant y require_permission se completarán en:
    - get_current_user → C-03 (auth-jwt-2fa)
    - get_tenant        → C-02 (core-models-y-tenancy)
    - require_permission → C-04 (rbac-permisos-finos)
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión async por request, cerrándola al finalizar.

    Uso:
        @router.get("/resource")
        async def handler(db: AsyncSession = Depends(get_db)):
            ...

    La sesión se cierra en el bloque finally aunque el handler lance excepción,
    evitando fugas de conexiones al pool de asyncpg.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ── RESERVADO → C-03 (auth-jwt-2fa) ──────────────────────────────────────────
# async def get_current_user(token: str = Depends(oauth2_scheme)) -> Usuario:
#     """Resuelve la identidad del usuario desde el JWT verificado.
#     NUNCA desde parámetros de URL o body — regla de oro de identidad."""
#     raise NotImplementedError("RESERVADO para C-03")


# ── RESERVADO → C-02 (core-models-y-tenancy) ─────────────────────────────────
# async def get_tenant(current_user = Depends(get_current_user)) -> Tenant:
#     """Resuelve el tenant desde la sesión verificada del usuario."""
#     raise NotImplementedError("RESERVADO para C-02")


# ── RESERVADO → C-04 (rbac-permisos-finos) ───────────────────────────────────
# def require_permission(permission: str):
#     """Guard de RBAC: verifica que el usuario tenga el permiso modulo:accion.
#     Sin permiso explícito → 403 (fail-closed)."""
#     raise NotImplementedError("RESERVADO para C-04")
