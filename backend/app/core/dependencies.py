"""Dependency injection de FastAPI.

- get_db: sesión async por request (asyncpg)
- get_current_user: resuelve identidad + tenant desde JWT verificado
- require_permission: guard RBAC modulo:accion (en permissions.py)
"""

import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.security import InvalidTokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


@dataclass
class CurrentUser:
    id: uuid.UUID
    tenant_id: uuid.UUID
    roles: list[str]
    impersonado_id: uuid.UUID | None = None
    jti: str | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    """Resuelve la identidad del usuario EXCLUSIVAMENTE desde el JWT verificado.

    Regla de oro: la identidad y el tenant NO se derivan de parámetros de la
    request — solo del token verificado server-side.

    Para tokens de impersonación (con impersonado_id + jti): verifica además
    que el JTI no esté en el blocklist de Redis (revocación explícita).
    """
    try:
        claims = decode_token(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if claims.get("scope") == "2fa_pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session incomplete — 2FA verification required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        impersonado_raw = claims.get("impersonado_id")
        impersonado_id = uuid.UUID(impersonado_raw) if impersonado_raw else None
        jti = claims.get("jti")
        user = CurrentUser(
            id=uuid.UUID(claims["sub"]),
            tenant_id=uuid.UUID(claims["tenant_id"]),
            roles=claims.get("roles", []),
            impersonado_id=impersonado_id,
            jti=jti,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if user.impersonado_id and user.jti:
        from app.core.redis_client import is_jti_revoked
        try:
            if await is_jti_revoked(user.jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Impersonation session revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception:
            # Redis no disponible: fail-closed — no permitir tokens no verificables
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
            )

    return user
