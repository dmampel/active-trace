"""Tests del endpoint GET /health.

Spec: health-check/spec.md
Ciclo TDD: RED → GREEN → TRIANGULATE → REFACTOR
"""

import pytest
from httpx import ASGITransport, AsyncClient


class TestHealthEndpoint:
    """Verifica el comportamiento del endpoint de salud."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, app_client: AsyncClient):
        """RED-05: GET /health responde 200 OK."""
        response = await app_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_is_json_with_status_ok(self, app_client: AsyncClient):
        """RED-05b: el cuerpo es JSON con campo status=ok."""
        response = await app_client.get("/health")
        body = response.json()
        assert body["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_includes_database_field(self, app_client: AsyncClient):
        """TRIANGULATE-05: la respuesta incluye campo database."""
        response = await app_client.get("/health")
        body = response.json()
        assert "database" in body
        # El campo database tiene un valor reconocible (up o down)
        assert body["database"] in ("up", "down")

    @pytest.mark.asyncio
    async def test_health_does_not_crash_when_called_multiple_times(self, app_client: AsyncClient):
        """TRIANGULATE-05b: el endpoint es estable en múltiples llamadas."""
        for _ in range(3):
            response = await app_client.get("/health")
            assert response.status_code == 200
