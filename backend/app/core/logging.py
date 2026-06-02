"""Logging estructurado en JSON para activia-trace.

Reemplaza el formatter por defecto por uno que emite una línea JSON por evento,
con campos timestamp, level y message. Aplica al logger raíz.

REGLA: nunca emitir secretos ni PII en texto claro en logs.
"""

import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str = "INFO") -> None:
    """Configura el logging raíz para emitir JSON estructurado.

    Args:
        level: nivel de log como string (INFO, DEBUG, WARNING, ERROR).

    Ejemplo de salida:
        {"timestamp": "2024-01-01T00:00:00Z", "level": "INFO", "message": "App iniciada"}
    """
    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Silenciar loggers muy verbosos de librerías de terceros
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retorna un logger con el nombre dado.

    Convenio: usar __name__ del módulo que lo invoca para trazabilidad.
    """
    return logging.getLogger(name)
