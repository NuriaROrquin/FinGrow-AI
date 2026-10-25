"""Configuracion de logging."""

import logging
import sys

from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from app.core.config import Settings

SERVICE_NAME = "fingrow-ai"
AXIOM_DATASET_HEADER = "X-Axiom-Dataset"

_UVICORN_LOGGERS = ("uvicorn", "uvicorn.access")
_EXPORTER_LOGGERS = ("opentelemetry", "urllib3", "requests")


def configure_logging(settings: Settings) -> LoggerProvider | None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = [h for h in uvicorn_logger.handlers if not isinstance(h, LoggingHandler)]

    if not settings.axiom_enabled:
        return None

    logger_provider = _build_axiom_logger_provider(settings)
    axiom_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    axiom_handler.addFilter(_is_not_from_the_exporter)

    root.addHandler(axiom_handler)
    for name in _UVICORN_LOGGERS:
        logging.getLogger(name).addHandler(axiom_handler)

    return logger_provider


def _build_axiom_logger_provider(settings: Settings) -> LoggerProvider:
    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "deployment.environment": settings.environment,
        }
    )
    exporter = OTLPLogExporter(
        endpoint=settings.axiom_logs_endpoint,
        headers={
            "Authorization": f"Bearer {settings.axiom_token}",
            AXIOM_DATASET_HEADER: settings.axiom_dataset,
        },
    )

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    return logger_provider


def _is_not_from_the_exporter(record: logging.LogRecord) -> bool:
    return not record.name.startswith(_EXPORTER_LOGGERS)
