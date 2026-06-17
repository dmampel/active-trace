"""Tests para MoodleWSClient con respx (mock httpx).

TDD Strict:
- RED: tests fallan porque el módulo no existe
- GREEN: implementar MoodleWSClient mínimo que pase los tests
- TRIANGULATE: múltiples casos (éxito, auth error, timeout)
"""
import pytest
import respx
from httpx import Response


class TestMoodleWSClientSuccess:
    @respx.mock
    async def test_get_course_participants_returns_list(self):
        from app.integrations.moodle_ws import MoodleWSClient

        moodle_url = "https://moodle.example.com"
        token = "abc123"
        course_id = 42

        mock_response = [
            {"firstname": "Juan", "lastname": "Pérez", "email": "juan@test.com"},
            {"firstname": "María", "lastname": "García", "email": "maria@test.com"},
        ]

        respx.get(f"{moodle_url}/webservice/rest/server.php").mock(
            return_value=Response(200, json=mock_response)
        )

        client = MoodleWSClient(moodle_url=moodle_url, token=token)
        participants = await client.get_course_participants(course_id)

        assert len(participants) == 2
        assert participants[0]["nombre"] == "Juan"
        assert participants[0]["apellidos"] == "Pérez"
        assert participants[0]["email"] == "juan@test.com"

    @respx.mock
    async def test_get_course_participants_empty_course(self):
        from app.integrations.moodle_ws import MoodleWSClient

        moodle_url = "https://moodle.example.com"
        token = "abc123"

        respx.get(f"{moodle_url}/webservice/rest/server.php").mock(
            return_value=Response(200, json=[])
        )

        client = MoodleWSClient(moodle_url=moodle_url, token=token)
        participants = await client.get_course_participants(99)

        assert participants == []


class TestMoodleWSClientAuthError:
    @respx.mock
    async def test_raises_moodle_auth_error_on_403(self):
        from app.integrations.moodle_ws import MoodleAuthError, MoodleWSClient

        moodle_url = "https://moodle.example.com"

        respx.get(f"{moodle_url}/webservice/rest/server.php").mock(
            return_value=Response(403, text="Forbidden")
        )

        client = MoodleWSClient(moodle_url=moodle_url, token="bad_token")
        with pytest.raises(MoodleAuthError):
            await client.get_course_participants(1)

    @respx.mock
    async def test_raises_moodle_auth_error_on_moodle_exception(self):
        """Moodle a veces retorna 200 con un JSON de error de tipo 'exception'."""
        from app.integrations.moodle_ws import MoodleAuthError, MoodleWSClient

        moodle_url = "https://moodle.example.com"

        respx.get(f"{moodle_url}/webservice/rest/server.php").mock(
            return_value=Response(200, json={
                "exception": "moodle_exception",
                "errorcode": "invalidsessionorloginrequired",
                "message": "Invalid token",
            })
        )

        client = MoodleWSClient(moodle_url=moodle_url, token="expired")
        with pytest.raises(MoodleAuthError):
            await client.get_course_participants(1)


class TestMoodleWSClientTimeout:
    @respx.mock
    async def test_raises_moodle_unavailable_on_timeout(self):
        import httpx
        from app.integrations.moodle_ws import MoodleUnavailableError, MoodleWSClient

        moodle_url = "https://moodle.example.com"

        respx.get(f"{moodle_url}/webservice/rest/server.php").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        client = MoodleWSClient(moodle_url=moodle_url, token="tok")
        with pytest.raises(MoodleUnavailableError):
            await client.get_course_participants(1)
