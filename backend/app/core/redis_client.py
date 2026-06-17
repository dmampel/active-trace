"""Cliente Redis async para blocklist de JTI de tokens de impersonación.

Responsabilidades:
- Pool de conexiones compartido (inicializado lazy en primer uso).
- is_jti_revoked: consulta si un JTI fue revocado (O(1)).
- revoke_jti: escribe el JTI con TTL en el blocklist.

TTL se fija igual al tiempo de expiración máximo del token, por lo que
las entradas se auto-limpian cuando el token ya no podría ser válido.
"""

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

_KEY_PREFIX = "jti_blocklist"

_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            get_settings().redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _pool


async def is_jti_revoked(jti: str) -> bool:
    """Retorna True si el JTI está en el blocklist de Redis."""
    async with Redis(connection_pool=_get_pool()) as r:
        return await r.exists(f"{_KEY_PREFIX}:{jti}") > 0


async def revoke_jti(jti: str, ttl_seconds: int) -> None:
    """Agrega el JTI al blocklist con TTL en segundos."""
    async with Redis(connection_pool=_get_pool()) as r:
        await r.setex(f"{_KEY_PREFIX}:{jti}", ttl_seconds, "1")
