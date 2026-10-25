"""Configuracion del servicio.

Equivalente a appsettings.json + IOptions<T> del backend .NET: los valores
se leen del entorno (o del archivo .env en desarrollo) y se validan al
arrancar. Si falta algo obligatorio, la app no levanta -- falla temprano y
con un mensaje claro, en vez de romper en el primer request.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Identidad del servicio -------------------------------------------
    app_name: str = "FinGrow AI"
    api_v1_prefix: str = "/api/v1"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # --- Seguridad entre servicios ----------------------------------------
    # El unico cliente de esta API es el backend .NET. No maneja usuarios
    # finales: valida que quien llama sea el backend, con un secreto compartido.
    api_key: str = Field(
        default="",
        description="Secreto compartido con FinGrow-BE. Vacio => auth deshabilitada (solo dev).",
    )
    api_key_header: str = "X-API-Key"

    # --- Proveedor de IA ---------------------------------------------------
    llm_provider: Literal["stub", "anthropic"] = "stub"
    llm_model: str = "claude-sonnet-5"
    llm_api_key: str = ""
    llm_timeout_seconds: int = Field(default=30, ge=1, le=300)

    transcription_provider: Literal["stub", "openai"] = "stub"
    transcription_model: str = "gpt-4o-mini-transcribe"
    transcription_api_key: str = ""
    transcription_timeout_seconds: int = Field(default=60, ge=1, le=300)
    transcription_language: str = Field(default="es", pattern=r"^[a-z]{2}$")
    transcription_max_audio_bytes: int = Field(default=20 * 1024 * 1024, ge=1, le=25_000_000)

    ocr_provider: Literal["stub", "textract"] = "stub"
    ocr_aws_region: str = "us-east-1"
    ocr_aws_access_key_id: str = ""
    ocr_aws_secret_access_key: str = ""
    ocr_timeout_seconds: int = Field(default=30, ge=1, le=300)
    ocr_max_document_bytes: int = Field(default=5 * 1024 * 1024, ge=1, le=5 * 1024 * 1024)

    axiom_token: str = ""
    axiom_dataset: str = ""
    axiom_domain: str = "api.axiom.co"

    @model_validator(mode="after")
    def _transcription_key_required(self) -> "Settings":
        if self.transcription_provider == "openai" and not self.transcription_api_key:
            raise ValueError("TRANSCRIPTION_API_KEY es obligatoria con TRANSCRIPTION_PROVIDER=openai.")

        return self

    @model_validator(mode="after")
    def _ocr_credentials_required(self) -> "Settings":
        if self.ocr_provider == "textract" and not (
            self.ocr_aws_access_key_id and self.ocr_aws_secret_access_key
        ):
            raise ValueError(
                "OCR_AWS_ACCESS_KEY_ID y OCR_AWS_SECRET_ACCESS_KEY son obligatorias "
                "con OCR_PROVIDER=textract."
            )

        return self

    @model_validator(mode="after")
    def _axiom_settings_complete(self) -> "Settings":
        if self.axiom_token and not self.axiom_dataset:
            raise ValueError("Para mandar los logs a Axiom falta AXIOM_DATASET.")

        if self.axiom_dataset and not self.axiom_token:
            raise ValueError("Para mandar los logs a Axiom falta AXIOM_TOKEN.")

        return self

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)

    @property
    def axiom_enabled(self) -> bool:
        return bool(self.axiom_token)

    @property
    def axiom_logs_endpoint(self) -> str:
        domain = self.axiom_domain.strip().rstrip("/") or "api.axiom.co"
        base_url = domain if "://" in domain else f"https://{domain}"
        return f"{base_url}/v1/logs"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la config una sola vez por proceso.

    lru_cache la convierte en singleton: la primera llamada la construye y
    valida, las siguientes devuelven la misma instancia.
    """
    return Settings()
