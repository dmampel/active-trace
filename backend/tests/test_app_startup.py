"""Tests de arranque de la app FastAPI.

Spec: app-scaffold/spec.md
Ciclo TDD: RED → GREEN → TRIANGULATE → REFACTOR
"""

import pytest
from httpx import AsyncClient


class TestAppStartup:
    """Verifica que la app FastAPI arranca y está operativa."""

    @pytest.mark.asyncio
    async def test_app_starts_without_error(self, app_client: AsyncClient):
        """RED-05d: la app se instancia y el ASGI lifespan completa sin error."""
        # Si la fixture app_client se crea, el lifespan completó correctamente.
        # Una simple request válida confirma que la app está operativa.
        response = await app_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_app_returns_404_for_unknown_route(self, app_client: AsyncClient):
        """TRIANGULATE: rutas no definidas retornan 404 (no 500)."""
        response = await app_client.get("/ruta-inexistente")
        assert response.status_code == 404
