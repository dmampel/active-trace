"""Worker placeholder — activia-trace.

Entrypoint mínimo del proceso de background jobs.
La tecnología real de la cola (asyncio propio / Celery / ARQ) es ADR-003,
abierta, se resuelve al construir el módulo de comunicaciones (C-12).

C-01 solo deja el servicio docker-compose y este entrypoint.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def main() -> None:
    """Loop no-op del worker.

    En C-12 se reemplazará por el consumidor real de la cola de comunicaciones.
    """
    logger.info("Worker iniciado (modo placeholder — ADR-003 pendiente)")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
