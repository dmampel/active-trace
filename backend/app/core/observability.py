"""Instrumentación OpenTelemetry para activia-trace — FastAPI.

Instrumenta la app con trazas HTTP via opentelemetry-instrumentation-fastapi.
Si no hay endpoint OTLP configurado, la app arranca igual sin exportar trazas.
El destino de exportación es configuración de despliegue, no del cimiento.
"""

import logging

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def configure_telemetry(app, service_name: str = "activia-trace", otlp_endpoint: str = "") -> None:
    """Inicializa OpenTelemetry para la app FastAPI.

    - Crea un TracerProvider con el nombre del servicio como resource.
    - Si otlp_endpoint no está vacío, configura exportación OTLP.
    - Instrumenta la app FastAPI para que cada request genere un span.
    - Si falta el exporter o hay error de conectividad, la app SIGUE funcionando.

    Args:
        app: instancia de FastAPI.
        service_name: nombre del servicio para el resource de OTel.
        otlp_endpoint: URL del collector OTLP. Vacío = sin exportación.
    """
    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OpenTelemetry: exportando trazas a %s", otlp_endpoint)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "OpenTelemetry: no se pudo configurar el exporter OTLP (%s). "
                "La app continúa sin exportar trazas.",
                exc,
            )
    else:
        logger.info("OpenTelemetry: sin endpoint OTLP configurado — trazas no exportadas.")

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
