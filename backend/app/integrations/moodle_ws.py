"""Cliente async para Moodle Web Services.

Responsabilidades:
- Llamar a la API WS de Moodle (core_enrol_get_enrolled_users)
- Mapear la respuesta al formato interno {nombre, apellidos, email}
- Propagar errores tipados: MoodleAuthError, MoodleUnavailableError

Recibe credenciales ya descifradas — nunca accede a la DB ni al módulo de seguridad.
"""

import httpx


# ── Excepciones tipadas ───────────────────────────────────────────────────────


class MoodleAuthError(Exception):
    """Token Moodle inválido, expirado o revocado."""


class MoodleUnavailableError(Exception):
    """Host Moodle no disponible (timeout, DNS, etc.)."""


# ── Cliente ───────────────────────────────────────────────────────────────────


class MoodleWSClient:
    """Cliente async para Moodle Web Services.

    Args:
        moodle_url: URL base de Moodle (e.g. https://moodle.example.com). Sin trailing slash.
        token: Token WS de Moodle ya descifrado.
    """

    WSFUNCTION = "core_enrol_get_enrolled_users"
    TIMEOUT_SECONDS = 10.0

    def __init__(self, moodle_url: str, token: str) -> None:
        self._base_url = moodle_url.rstrip("/")
        self._token = token

    async def get_course_participants(self, course_id: int) -> list[dict]:
        """Obtiene los participantes de un curso Moodle.

        Args:
            course_id: ID del curso en Moodle.

        Returns:
            Lista de dicts con claves 'nombre', 'apellidos', 'email'.

        Raises:
            MoodleAuthError: si Moodle responde 403 o devuelve un error de auth.
            MoodleUnavailableError: si hay timeout o el host no responde.
        """
        params = {
            "wstoken": self._token,
            "wsfunction": self.WSFUNCTION,
            "moodlewsrestformat": "json",
            "courseid": course_id,
        }

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{self._base_url}/webservice/rest/server.php",
                    params=params,
                )
        except httpx.TimeoutException as exc:
            raise MoodleUnavailableError(
                "Moodle no disponible. Intentar más tarde."
            ) from exc
        except httpx.HTTPError as exc:
            raise MoodleUnavailableError(
                f"Error de red al contactar Moodle: {exc}"
            ) from exc

        if response.status_code == 403:
            raise MoodleAuthError(
                "Error de autenticación con Moodle. Verificar token."
            )

        if response.status_code != 200:
            raise MoodleUnavailableError(
                f"Moodle retornó HTTP {response.status_code}."
            )

        data = response.json()

        # Moodle puede retornar 200 con un JSON de excepción
        if isinstance(data, dict) and "exception" in data:
            raise MoodleAuthError(
                f"Moodle WS error: {data.get('message', data.get('exception'))}"
            )

        return [self._map_participant(p) for p in data]

    @staticmethod
    def _map_participant(raw: dict) -> dict:
        """Mapea un participante de Moodle al formato interno."""
        return {
            "nombre": raw.get("firstname", ""),
            "apellidos": raw.get("lastname", ""),
            "email": raw.get("email", ""),
        }
