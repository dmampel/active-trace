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

from app.core.config import Settings
from app.core.database import dispose_engine, init_engine
from app.core.logging import configure_logging
from app.core.observability import configure_telemetry
from app.api.v1.routers import health as health_router


def _build_app() -> FastAPI:
    """Construye la instancia de FastAPI con lifespan y routers registrados."""
    settings = Settings()

    # Logging JSON antes de cualquier otra cosa
    configure_logging(level="DEBUG" if settings.environment == "development" else "INFO")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan: inicializa recursos al arrancar, los descarta al apagar."""
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
        # La documentación OpenAPI solo se expone fuera de producción
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    # OpenTelemetry — sin exporter si OTLP_ENDPOINT está vacío
    configure_telemetry(app, otlp_endpoint=settings.otlp_endpoint)

    # Routers
    app.include_router(health_router.router)

    return app


app = _build_app()
