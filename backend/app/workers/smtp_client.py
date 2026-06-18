"""Cliente SMTP para despacho de comunicaciones salientes (C-12).

SmtpClient es la interfaz/stub:
- Método async send(to, subject, body) → bool
- Implementación real lee SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS del entorno

En tests se usa un stub/mock que reemplaza esta implementación.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class SmtpClient:
    """Cliente SMTP real. Lee configuración de variables de entorno.

    Variables de entorno:
        SMTP_HOST  — servidor SMTP (default: localhost)
        SMTP_PORT  — puerto SMTP (default: 587)
        SMTP_USER  — usuario para autenticación (opcional)
        SMTP_PASS  — contraseña para autenticación (opcional)
        SMTP_FROM  — dirección remitente (default: noreply@activia-trace.io)
    """

    def __init__(self) -> None:
        self._host = os.getenv("SMTP_HOST", "localhost")
        self._port = int(os.getenv("SMTP_PORT", "587"))
        self._user = os.getenv("SMTP_USER")
        self._password = os.getenv("SMTP_PASS")
        self._from = os.getenv("SMTP_FROM", "noreply@activia-trace.io")

    async def send(self, to: str, subject: str, body: str) -> bool:
        """Envía un email via SMTP.

        Returns:
            True si el envío fue exitoso, False si falló.

        Raises:
            Exception: si el envío falló (el caller decide cómo manejarla).
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = to
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self._host, self._port) as smtp:
                smtp.ehlo()
                smtp.starttls()
                if self._user and self._password:
                    smtp.login(self._user, self._password)
                smtp.sendmail(self._from, [to], msg.as_string())
            logger.info("Email sent to %s", to)
            return True
        except Exception as exc:
            logger.error("SMTP send failed to %s: %s", to, exc)
            raise
