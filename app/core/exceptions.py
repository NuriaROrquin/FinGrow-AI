"""Excepciones propias del servicio.

Son el equivalente a los Error / DomainException del backend .NET: no
representan un bug, sino un caso previsto que hay que comunicarle al que
llamo. app/api/error_handlers.py las traduce a la respuesta HTTP.

`code` es un identificador estable pensado para que el AiService de .NET
lo mapee a su propio Error sin parsear el mensaje.
"""


class FinGrowAiError(Exception):
    """Base de todos los errores esperables del servicio."""

    code: str = "ai_error"
    status_code: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidInputError(FinGrowAiError):
    """La entrada es sintacticamente valida pero no tiene sentido de negocio."""

    code = "invalid_input"
    status_code = 422


class ModelUnavailableError(FinGrowAiError):
    """El proveedor de IA no respondio o esta caido."""

    code = "model_unavailable"
    status_code = 503


class InferenceFailedError(FinGrowAiError):
    """El modelo respondio, pero la respuesta no se pudo interpretar."""

    code = "inference_failed"
    status_code = 502
