from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str = Field(min_length=1, description="Texto transcrito, listo para message-parsing.")
    language: str = Field(description="Idioma con el que se transcribio, en ISO-639-1.")
    model: str = Field(description="Modelo que produjo el resultado, para trazabilidad.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Gasté 2500 pesos en el súper con débito",
                    "language": "es",
                    "model": "gpt-4o-mini-transcribe",
                }
            ]
        }
    }
