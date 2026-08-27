"""Traduccion de excepciones a respuestas HTTP.

Mismo rol que ExceptionHandlingMiddleware.cs del backend: un solo lugar donde
las excepciones se convierten en JSON, para que ninguna ruta tenga que
envolver su logica en try/except.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import FinGrowAiError
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(FinGrowAiError)
    async def handle_known_error(_: Request, exc: FinGrowAiError) -> JSONResponse:
        logger.warning("%s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(code=exc.code, message=exc.message).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI ya devuelve 422 con su propio formato. Lo reescribimos para
        # que TODOS los errores de la API salgan con la misma forma.
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                code="validation_error",
                message=f"El request no cumple el contrato: {exc.errors()}",
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(code="http_error", message=str(exc.detail)).model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # Lo inesperado se loguea completo pero no se le cuenta al que llama:
        # un stack trace en la respuesta filtra detalles internos.
        logger.exception("Error no controlado", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                code="internal_error",
                message="Ocurrio un error interno en el servicio de IA.",
            ).model_dump(),
        )
