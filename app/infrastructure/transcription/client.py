import logging
import time
from typing import Protocol

import openai
from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.exceptions import AudioNotUnderstoodError, ModelUnavailableError
from app.domain.enums import AudioFormat
from app.infrastructure.prompts.transcription import TRANSCRIPTION_PROMPT

logger = logging.getLogger(__name__)

STUB_TRANSCRIPT = "Gasté 2500 pesos en el súper con débito"


class Transcriber(Protocol):
    model: str

    async def transcribe(self, audio: bytes, *, audio_format: AudioFormat, language: str) -> str: ...


class StubTranscriber:
    def __init__(self, model: str) -> None:
        self.model = model

    async def transcribe(self, audio: bytes, *, audio_format: AudioFormat, language: str) -> str:
        return STUB_TRANSCRIPT


class OpenAiTranscriber:
    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)
        self.model = model

    async def transcribe(self, audio: bytes, *, audio_format: AudioFormat, language: str) -> str:
        started = time.perf_counter()
        try:
            transcription = await self._client.audio.transcriptions.create(
                model=self.model,
                file=(f"audio.{audio_format}", audio),
                language=language,
                prompt=TRANSCRIPTION_PROMPT,
            )
        except (openai.APITimeoutError, openai.APIConnectionError) as exc:
            raise ModelUnavailableError("El proveedor de transcripcion no respondio a tiempo.") from exc
        except openai.RateLimitError as exc:
            raise ModelUnavailableError(
                "El proveedor de transcripcion esta limitando las requests (rate limit o cuota agotada)."
            ) from exc
        except openai.AuthenticationError as exc:
            logger.error("TRANSCRIPTION_API_KEY invalida o vencida: %s", exc)
            raise ModelUnavailableError("El proveedor de transcripcion rechazo las credenciales.") from exc
        except openai.BadRequestError as exc:
            logger.warning("El proveedor de transcripcion rechazo el audio: %s", exc)
            raise AudioNotUnderstoodError("El audio no se pudo procesar: puede estar danado.") from exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                raise ModelUnavailableError(
                    "El proveedor de transcripcion respondio con un error interno."
                ) from exc
            raise

        duration_ms = round((time.perf_counter() - started) * 1000)
        logger.info(
            "Audio %s de %d bytes transcripto con %s en %d ms",
            audio_format,
            len(audio),
            self.model,
            duration_ms,
            extra={"model": self.model, "duration_ms": duration_ms, "audio_bytes": len(audio)},
        )
        return transcription.text


def build_transcriber(settings: Settings) -> Transcriber:
    if settings.transcription_provider == "openai":
        return OpenAiTranscriber(
            api_key=settings.transcription_api_key,
            model=settings.transcription_model,
            timeout_seconds=settings.transcription_timeout_seconds,
        )
    return StubTranscriber(model=settings.transcription_model)
