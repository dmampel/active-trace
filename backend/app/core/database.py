"""Motor async de SQLAlchemy 2.0 + factory de sesiones.

Implementa el patrón sesión-por-request para FastAPI con asyncpg.
El engine se crea una sola vez en el lifespan de la app.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# ── Base declarativa ──────────────────────────────────────────────────────────
# Todos los modelos de dominio heredan de esta Base.
# Se centraliza aquí para que Alembic pueda descubrir los metadatos.


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy para todos los modelos de activia-trace."""


# ── Engine y factory de sesiones ─────────────────────────────────────────────
# Inicializados a None; se configuran en el lifespan de FastAPI.

_engine = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> None:
    """Inicializa el engine async y la factory de sesiones.

    Llamar una sola vez desde el lifespan de la app.
    No reutilizar engines entre tests — cada test suite crea el suyo.
    """
    global _engine, _async_session_factory  # noqa: PLW0603

    _engine = create_async_engine(
        database_url,
        echo=False,          # logs de SQL desactivados por defecto; activar solo en debug
        pool_pre_ping=True,  # verifica conexiones stale antes de usarlas
    )
    _async_session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,  # evita lazy-load post-commit en contexto async
        class_=AsyncSession,
    )


def get_engine():
    """Devuelve el engine inicializado.

    Raises:
        RuntimeError: si se llama antes de init_engine().
    """
    if _engine is None:
        raise RuntimeError(
            "El engine no fue inicializado. Llamar a init_engine() en el lifespan."
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Devuelve la factory de sesiones async.

    Raises:
        RuntimeError: si se llama antes de init_engine().
    """
    if _async_session_factory is None:
        raise RuntimeError(
            "La factory de sesiones no fue inicializada. Llamar a init_engine() en el lifespan."
        )
    return _async_session_factory


async def dispose_engine() -> None:
    """Descarta el engine y cierra todas las conexiones del pool.

    Llamar desde el lifespan al cerrar la app o al teardown de tests.
    """
    global _engine, _async_session_factory  # noqa: PLW0603

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
