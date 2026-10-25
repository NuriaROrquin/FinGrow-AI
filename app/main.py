"""Punto de entrada y cableado de la aplicacion.

Equivalente a Program.cs: el unico archivo que conoce todas las capas y las
conecta. Todo lo demas depende hacia adentro.

Para levantarlo en local:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.security import require_api_key
from app.api.v1.router import api_router
from app.api.v1.routes import health
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.llm.client import build_llm_client
from app.infrastructure.ocr.client import build_receipt_reader
from app.infrastructure.transcription.client import build_transcriber


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Se ejecuta una vez al arrancar y una vez al apagar.

    Aca va lo caro de construir, para no rehacerlo en cada request: clientes,
    conexiones y -- sobre todo -- modelos de ML. Cargar un modelo tarda
    segundos; hacerlo por request mata la API.
    """
    settings = get_settings()
    logger_provider = configure_logging(settings)

    app.state.llm_client = build_llm_client(settings)
    app.state.transcriber = build_transcriber(settings)
    app.state.receipt_reader = build_receipt_reader(settings)
    yield
    if logger_provider is not None:
        logger_provider.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Servicio de IA de FinGrow. Su unico cliente es el backend .NET "
            "(FinGrow-BE); el frontend nunca le pega directo."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    register_error_handlers(app)

    # Sin prefijo ni auth: el backend .NET lo consume como GET /health.
    app.include_router(health.router)

    # El resto va versionado y detras de la API key.
    app.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
        dependencies=[Depends(require_api_key)],
    )

    return app


app = create_app()
