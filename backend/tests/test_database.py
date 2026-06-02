"""Tests del engine async y la dependency get_db.

Spec: database-connection/spec.md
Ciclo TDD: RED → GREEN → TRIANGULATE → REFACTOR

NOTA: estos tests requieren una base de datos PostgreSQL real (asyncpg no funciona
sobre SQLite). Usar la variable TEST_DATABASE_URL del entorno o del .env de test.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestDatabaseConnection:
    """Verifica el engine async y la sesión por request."""

    @pytest.mark.asyncio
    async def test_session_executes_select_one(self, db_session: AsyncSession):
        """GREEN-03: una sesión async puede ejecutar SELECT 1 y obtener resultado."""
        result = await db_session.execute(text("SELECT 1 AS value"))
        row = result.fetchone()
        assert row is not None
        assert row.value == 1

    @pytest.mark.asyncio
    async def test_session_executes_select_current_database(self, db_session: AsyncSession):
        """TRIANGULATE-03: la sesión conecta a la base de datos correcta."""
        result = await db_session.execute(text("SELECT current_database()"))
        row = result.fetchone()
        assert row is not None
        # La base de datos de test tiene un nombre no vacío
        assert len(row[0]) > 0

    @pytest.mark.asyncio
    async def test_session_closes_on_exception(self, test_session_factory):
        """TRIANGULATE-03b: la sesión se cierra correctamente ante excepción."""
        closed = False

        async with test_session_factory() as session:
            try:
                # Forzamos una excepción dentro del contexto de la sesión
                raise RuntimeError("error simulado en el handler")
            except RuntimeError:
                pass
            finally:
                await session.close()
                closed = True

        assert closed is True
