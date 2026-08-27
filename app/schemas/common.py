"""Contratos compartidos por todos los endpoints."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Forma unica de error de toda la API.

    Que todos los errores salgan con esta forma es lo que le permite al
    AiService de .NET mapearlos a Error/Result sin casos especiales.
    """

    code: str = Field(description="Identificador estable del error.")
    message: str = Field(description="Descripcion legible. No parsear.")

    model_config = {
        "json_schema_extra": {
            "examples": [{"code": "model_unavailable", "message": "El proveedor de IA no respondio."}]
        }
    }


class HealthResponse(BaseModel):
    """Respuesta de GET /health.

    El backend .NET (AiService.IsHealthyAsync) solo mira el status code, pero
    devolver el detalle sirve para diagnosticar a mano.
    """

    status: str = "ok"
    service: str
    environment: str
