"""Bootstrap de la aplicación FastAPI — activia-trace backend.

Responsabilidades de este módulo:
- Inicializar logging JSON estructurado
- Inicializar el engine async de SQLAlchemy (lifespan)
- Registrar routers
- Inicializar OpenTelemetry (sin bloquear si no hay exporter configurado)

NO hay lógica de negocio aquí — solo wiring.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import Settings
from app.core.limiter import limiter
from app.core.database import dispose_engine, init_engine
from app.core.logging import configure_logging
from app.core.observability import configure_telemetry
from app.api.v1.routers import health as health_router
from app.api.v1.routers import auth as auth_router


def _build_app() -> FastAPI:
    """Construye la instancia de FastAPI con lifespan y routers registrados."""
    settings = Settings()

    configure_logging(level="DEBUG" if settings.environment == "development" else "INFO")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_engine(settings.database_url)
        yield
        await dispose_engine()

    app = FastAPI(
        title="activia-trace API",
        description=(
            "Plataforma de gestión académica y trazabilidad multi-tenant "
            "sobre Moodle. Cada institución es un tenant aislado; todo audita."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting (slowapi) — instancia compartida con los routers
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    configure_telemetry(app, otlp_endpoint=settings.otlp_endpoint)

    from app.api.v1.routers import me as me_router
    from app.api.v1.routers import estructura as estructura_router
    from app.api.v1.routers import usuarios as usuarios_router
    from app.api.v1.routers import asignaciones as asignaciones_router
    from app.api.v1.routers import equipos as equipos_router
    app.include_router(health_router.router)
    app.include_router(auth_router.router)
    app.include_router(me_router.router)
    app.include_router(estructura_router.router)
    app.include_router(usuarios_router.router)
    app.include_router(asignaciones_router.router)
    app.include_router(equipos_router.router)

    return app


app = _build_app()
