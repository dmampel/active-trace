"""Tests de la configuración tipada (Settings) — Pydantic v2 / pydantic-settings.

Spec: app-configuration/spec.md
Ciclo TDD: RED → GREEN → TRIANGULATE → REFACTOR
"""

import pytest
from pydantic import ValidationError


class TestSettings:
    """Verifica que Settings valida correctamente las variables de entorno."""

    def test_settings_instantiates_with_valid_env(self, monkeypatch):
        """RED-01: Settings se instancia con variables de entorno válidas."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
        monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db_test")
        monkeypatch.setenv("SECRET_KEY", "a" * 64)
        monkeypatch.setenv("ENCRYPTION_KEY", "b" * 64)

        from app.core.config import Settings

        settings = Settings()
        assert settings.database_url == "postgresql+asyncpg://u:p@localhost/db"
        assert settings.access_token_expire_minutes == 15  # default

    def test_settings_access_token_default(self, monkeypatch):
        """TRIANGULATE-01: ACCESS_TOKEN_EXPIRE_MINUTES tiene default 15."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
        monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db_test")
        monkeypatch.setenv("SECRET_KEY", "a" * 64)
        monkeypatch.setenv("ENCRYPTION_KEY", "b" * 64)

        from app.core.config import Settings

        settings = Settings()
        assert settings.access_token_expire_minutes == 15

    def test_settings_fails_when_secret_key_missing(self, monkeypatch):
        """TRIANGULATE-02: Sin SECRET_KEY la instanciación debe fallar."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
        monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db_test")
        monkeypatch.setenv("ENCRYPTION_KEY", "b" * 64)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        from importlib import reload
        import app.core.config as cfg_module

        reload(cfg_module)
        from app.core.config import Settings  # noqa: F811

        with pytest.raises((ValidationError, ValueError)):
            Settings()

    def test_settings_fails_when_database_url_missing(self, monkeypatch):
        """TRIANGULATE-03: Sin DATABASE_URL la instanciación debe fallar."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db_test")
        monkeypatch.setenv("SECRET_KEY", "a" * 64)
        monkeypatch.setenv("ENCRYPTION_KEY", "b" * 64)

        from importlib import reload
        import app.core.config as cfg_module

        reload(cfg_module)
        from app.core.config import Settings  # noqa: F811

        with pytest.raises((ValidationError, ValueError)):
            Settings()
