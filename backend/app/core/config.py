"""Configuración tipada de activia-trace usando Pydantic v2 / pydantic-settings.

Carga variables desde el entorno (o archivo .env). Falla en arranque si falta
alguna variable requerida o el valor no supera la validación.

Todos los valores sensibles (SECRET_KEY, ENCRYPTION_KEY) se validan en largo;
nunca se loguean en texto claro.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de configuración de la aplicación.

    Se cargan desde el entorno en orden: variables de proceso → archivo .env.
    Fallar rápido en arranque si falta alguna variable requerida.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Base de datos ──────────────────────────────────────────────────────────
    database_url: str = Field(
        ...,
        description="URL de conexión async a PostgreSQL (asyncpg). Requerida.",
    )
    test_database_url: str = Field(
        ...,
        description="URL de conexión async a la DB de test. Requerida.",
    )

    # ── Seguridad ──────────────────────────────────────────────────────────────
    secret_key: str = Field(
        ...,
        description="Clave secreta para firmar JWT. Mínimo 64 caracteres hex.",
    )
    encryption_key: str = Field(
        ...,
        description="Clave AES-256 para cifrar PII en reposo. Mínimo 64 caracteres hex.",
    )

    # ── Tokens ────────────────────────────────────────────────────────────────
    access_token_expire_minutes: int = Field(
        default=15,
        ge=1,
        description="Duración del access token en minutos. Default: 15.",
    )
    refresh_token_expire_days: int = Field(
        default=30,
        ge=1,
        description="Duración del refresh token en días. Default: 30.",
    )
    impersonation_token_expire_minutes: int = Field(
        default=60,
        ge=1,
        description="Duración del token de impersonación en minutos. Default: 60.",
    )

    # ── Entorno ───────────────────────────────────────────────────────────────
    environment: str = Field(
        default="development",
        description="Entorno de ejecución: development | production | test.",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Orígenes permitidos por CORS. En producción, especificá los dominios exactos del frontend.",
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL de conexión a Redis para blocklist de JTI de impersonación.",
    )

    # ── OpenTelemetry ─────────────────────────────────────────────────────────
    otlp_endpoint: str = Field(
        default="",
        description="Endpoint OTLP para exportación de trazas. Vacío = sin exportación.",
    )

    # ── Validaciones ──────────────────────────────────────────────────────────

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_long_enough(cls, v: str) -> str:
        if len(v) < 64:
            raise ValueError(
                "SECRET_KEY debe tener al menos 64 caracteres. "
                "Generá uno con: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @field_validator("encryption_key")
    @classmethod
    def encryption_key_must_be_long_enough(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "ENCRYPTION_KEY debe tener al menos 32 caracteres. "
                "Generá uno con: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @field_validator("database_url", "test_database_url")
    @classmethod
    def database_url_must_use_asyncpg(cls, v: str) -> str:
        if "asyncpg" not in v and "postgresql+asyncpg" not in v:
            raise ValueError(
                f"DATABASE_URL debe usar el driver asyncpg. Valor recibido: '{v}'"
            )
        return v

    def __repr__(self) -> str:
        """No exponer valores sensibles en repr."""
        return (
            f"Settings(environment={self.environment!r}, "
            f"database_url=<redacted>, "
            f"access_token_expire_minutes={self.access_token_expire_minutes})"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
