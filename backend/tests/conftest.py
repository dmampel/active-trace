"""Fixtures compartidas para la suite de tests de activia-trace backend.

Estrategia de DB:
- Se usa una base de datos PostgreSQL real (TEST_DATABASE_URL del entorno).
- asyncpg no levanta sobre SQLite — es por diseño: el smoke valida la conexión real.
- El engine de test se crea y descarta por sesión (scope=session) para eficiencia.
- Cada test recibe su propia sesión (scope=function) para aislamiento.

Variables de entorno requeridas para tests de DB:
    TEST_DATABASE_URL=postgresql+asyncpg://user:pass@host/db_test
"""

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings cargado con variables de entorno de test.

    Requiere: DATABASE_URL, TEST_DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY en el entorno
    o en backend/.env (que se levanta automáticamente por pydantic-settings).
    """
    # Asegurar que hay un entorno mínimo para tests si no hay .env
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
    os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
    os.environ.setdefault("SECRET_KEY", "a" * 64)
    os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)
    return Settings()


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_settings: Settings):
    """Engine async de SQLAlchemy para tests (scope=session: reutilizado por todos).

    Usa NullPool para evitar el conflicto de event loop entre tests async:
    asyncpg no puede reutilizar conexiones creadas en un loop distinto al actual.
    """
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(
        test_settings.test_database_url,
        echo=False,
        poolclass=NullPool,  # sin pool: cada test abre y cierra su propia conexión
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def create_tables(test_engine):
    """Crea todas las tablas en la DB de test al inicio de la sesión.

    No se usa autouse — solo se activa cuando db_session o app_client la requieren.
    Eso evita que tests con TestClient (que no usan PG real) fallen por DB inexistente.
    """
    from app.models.base import Base
    import app.models  # noqa: F401 — registra todos los modelos incluyendo asignacion, estructura

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine, create_tables):
    """Factory de sesiones async para tests."""
    factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return factory


@pytest_asyncio.fixture
async def db_session(test_session_factory) -> AsyncSession:
    """Sesión async aislada por test.

    Cada test recibe una sesión fresca; se cierra al finalizar el test.
    No se hace rollback global — los tests de smoke solo leen, no escriben.
    """
    async with test_session_factory() as session:
        yield session
        await session.close()


@pytest_asyncio.fixture
async def app_client(test_settings):
    """AsyncClient HTTP conectado a la app FastAPI con engine de test.

    Usa 'async with AsyncClient(app=app)' que activa el lifespan de FastAPI,
    incluyendo init_engine(). Sin esto, get_db falla con RuntimeError.
    """
    import os
    import importlib

    os.environ["DATABASE_URL"] = test_settings.test_database_url
    os.environ["TEST_DATABASE_URL"] = test_settings.test_database_url
    os.environ["SECRET_KEY"] = test_settings.secret_key
    os.environ["ENCRYPTION_KEY"] = test_settings.encryption_key

    # Recargar para capturar los env vars actualizados
    import app.core.database as db_module
    import app.main as main_module
    importlib.reload(db_module)
    importlib.reload(main_module)
    from app.main import app

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        # Inicializar engine manualmente (el lifespan no se dispara en ASGI test)
        from app.core.database import init_engine, dispose_engine
        init_engine(test_settings.test_database_url)
        try:
            yield client
        finally:
            await dispose_engine()
