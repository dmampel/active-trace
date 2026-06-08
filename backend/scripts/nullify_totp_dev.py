"""Script de re-encrypt en dev: NULL-ea los campos TOTP cifrados con Fernet (AES-128).

Ejecutar UNA VEZ después de deployar AES256GCMCipher en un entorno de desarrollo.
En producción no hay datos reales — este script no aplica a prod.

Uso:
    cd backend
    python scripts/nullify_totp_dev.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace")

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


async def nullify_totp_fields() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as conn:
        result = await conn.execute(
            text("UPDATE \"user\" SET totp_secret_enc = NULL, totp_pending_secret_enc = NULL "
                 "WHERE totp_secret_enc IS NOT NULL OR totp_pending_secret_enc IS NOT NULL")
        )
        print(f"Rows updated: {result.rowcount}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(nullify_totp_fields())
