"""Tests del módulo redis_client — Strict TDD.

No requieren Redis real: mockean el cliente async para testear
la lógica de is_jti_revoked y revoke_jti en aislamiento.
"""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)


# ── is_jti_revoked ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_is_jti_revoked_returns_true_when_key_exists():
    """is_jti_revoked retorna True si la clave existe en Redis."""
    from app.core.redis_client import is_jti_revoked

    mock_redis = AsyncMock()
    mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_redis.__aexit__ = AsyncMock(return_value=False)
    mock_redis.exists = AsyncMock(return_value=1)

    with patch("app.core.redis_client.Redis", return_value=mock_redis):
        result = await is_jti_revoked("some-jti")

    assert result is True
    mock_redis.exists.assert_called_once_with("jti_blocklist:some-jti")


@pytest.mark.asyncio
async def test_is_jti_revoked_returns_false_when_key_absent():
    """is_jti_revoked retorna False si la clave no existe en Redis."""
    from app.core.redis_client import is_jti_revoked

    mock_redis = AsyncMock()
    mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_redis.__aexit__ = AsyncMock(return_value=False)
    mock_redis.exists = AsyncMock(return_value=0)

    with patch("app.core.redis_client.Redis", return_value=mock_redis):
        result = await is_jti_revoked("unknown-jti")

    assert result is False


# ── revoke_jti ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_revoke_jti_calls_setex_with_correct_key_and_ttl():
    """revoke_jti escribe la clave con el TTL correcto en Redis."""
    from app.core.redis_client import revoke_jti

    mock_redis = AsyncMock()
    mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_redis.__aexit__ = AsyncMock(return_value=False)
    mock_redis.setex = AsyncMock()

    with patch("app.core.redis_client.Redis", return_value=mock_redis):
        await revoke_jti("abc-123", ttl_seconds=3600)

    mock_redis.setex.assert_called_once_with("jti_blocklist:abc-123", 3600, "1")


@pytest.mark.asyncio
async def test_revoke_jti_key_is_readable_after_write():
    """Triangulación: distintos JTIs producen claves distintas."""
    from app.core.redis_client import revoke_jti

    calls = []

    mock_redis = AsyncMock()
    mock_redis.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_redis.__aexit__ = AsyncMock(return_value=False)
    mock_redis.setex = AsyncMock(side_effect=lambda k, ttl, v: calls.append(k))

    with patch("app.core.redis_client.Redis", return_value=mock_redis):
        await revoke_jti("jti-A", ttl_seconds=60)
        await revoke_jti("jti-B", ttl_seconds=60)

    assert "jti_blocklist:jti-A" in calls
    assert "jti_blocklist:jti-B" in calls
    assert calls[0] != calls[1]
