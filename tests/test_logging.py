import logging
import threading
from collections.abc import Iterator
from email.message import Message
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import AXIOM_DATASET_HEADER, SERVICE_NAME, configure_logging


class FakeOtlpCollector:
    def __init__(self) -> None:
        self.requests: list[tuple[str, Message, bytes]] = []
        collector = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers["Content-Length"]))
                collector.requests.append((self.path, self.headers, body))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"


@pytest.fixture
def collector() -> Iterator[FakeOtlpCollector]:
    fake = FakeOtlpCollector()
    fake.thread.start()
    yield fake
    fake.server.shutdown()
    fake.server.server_close()


@pytest.fixture(autouse=True)
def _restore_logging() -> Iterator[None]:
    names = ("", "uvicorn", "uvicorn.access")
    saved = {name: (logging.getLogger(name).handlers[:], logging.getLogger(name).level) for name in names}
    yield
    for name, (handlers, level) in saved.items():
        logging.getLogger(name).handlers = handlers
        logging.getLogger(name).setLevel(level)


def test_logs_reach_the_otlp_logs_endpoint_with_the_token_and_the_dataset(collector: FakeOtlpCollector):
    settings = Settings(
        axiom_token="xaat-test-token",
        axiom_dataset="fingrow-test",
        axiom_domain=collector.base_url,
        log_level="DEBUG",
    )

    logger_provider = configure_logging(settings)
    logging.getLogger("app.infrastructure.llm.client").debug("Prompt armado para el modelo")
    logging.getLogger("app.services.categorization_service").info("Categoria propuesta: alimentos")
    logging.getLogger("uvicorn.access").info("POST /api/v1/categorization 200")
    logging.getLogger("urllib3.connectionpool").warning("Conexion reintentada con Axiom")
    logger_provider.shutdown()

    assert len(collector.requests) >= 1
    path, headers, _ = collector.requests[0]
    body = b"".join(request[2] for request in collector.requests)
    assert path == "/v1/logs"
    assert headers.get("Authorization") == "Bearer xaat-test-token"
    assert headers.get(AXIOM_DATASET_HEADER) == "fingrow-test"
    assert SERVICE_NAME.encode() in body
    assert b"development" in body
    assert b"Categoria propuesta: alimentos" in body
    assert b"POST /api/v1/categorization 200" in body
    assert b"Conexion reintentada con Axiom" not in body
    assert b"Prompt armado para el modelo" not in body


def test_without_axiom_only_the_console_handler_is_configured():
    logger_provider = configure_logging(Settings())

    assert logger_provider is None
    assert not any(isinstance(h, LoggingHandler) for h in logging.getLogger().handlers)
    assert not any(isinstance(h, LoggingHandler) for h in logging.getLogger("uvicorn").handlers)


def test_configuring_twice_does_not_duplicate_the_axiom_handler(collector: FakeOtlpCollector):
    settings = Settings(
        axiom_token="xaat-test-token", axiom_dataset="fingrow-test", axiom_domain=collector.base_url
    )

    configure_logging(settings).shutdown()
    configure_logging(settings).shutdown()

    handlers = logging.getLogger("uvicorn.access").handlers
    assert sum(isinstance(h, LoggingHandler) for h in handlers) == 1


@pytest.mark.parametrize(
    ("token", "dataset", "missing"),
    [("xaat-test-token", "", "AXIOM_DATASET"), ("", "fingrow-test", "AXIOM_TOKEN")],
)
def test_half_configured_axiom_stops_the_startup_naming_what_is_missing(
    token: str, dataset: str, missing: str
):
    with pytest.raises(ValidationError, match=missing):
        Settings(axiom_token=token, axiom_dataset=dataset)


@pytest.mark.parametrize(
    ("domain", "endpoint"),
    [
        ("api.axiom.co", "https://api.axiom.co/v1/logs"),
        ("", "https://api.axiom.co/v1/logs"),
        ("eu-central-1.aws.edge.axiom.co/", "https://eu-central-1.aws.edge.axiom.co/v1/logs"),
        ("http://127.0.0.1:4318", "http://127.0.0.1:4318/v1/logs"),
    ],
)
def test_the_logs_endpoint_is_built_from_the_domain(domain: str, endpoint: str):
    assert Settings(axiom_domain=domain).axiom_logs_endpoint == endpoint
