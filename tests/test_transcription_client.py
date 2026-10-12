from unittest.mock import AsyncMock

import httpx2
import openai
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import AudioNotUnderstoodError, ModelUnavailableError
from app.domain.enums import AudioFormat
from app.infrastructure.prompts.transcription import TRANSCRIPTION_PROMPT
from app.infrastructure.transcription.client import (
    STUB_TRANSCRIPT,
    OpenAiTranscriber,
    StubTranscriber,
    build_transcriber,
)

_URL = "https://api.openai.com/v1/audio/transcriptions"


class _FakeTranscription:
    def __init__(self, text: str) -> None:
        self.text = text


def _make_transcriber() -> OpenAiTranscriber:
    return OpenAiTranscriber(api_key="test-key", model="gpt-4o-mini-transcribe", timeout_seconds=5)


def _status_error(cls: type[openai.APIStatusError], status_code: int) -> openai.APIStatusError:
    request = httpx2.Request("POST", _URL)
    response = httpx2.Response(status_code, request=request)
    return cls("boom", response=response, body=None)


async def _transcribe(transcriber: OpenAiTranscriber) -> str:
    return await transcriber.transcribe(b"audio", audio_format=AudioFormat.OGG, language="es")


async def test_devuelve_el_texto_transcrito() -> None:
    transcriber = _make_transcriber()
    transcriber._client.audio.transcriptions.create = AsyncMock(
        return_value=_FakeTranscription("gaste 2500 en el super")
    )

    assert await _transcribe(transcriber) == "gaste 2500 en el super"


async def test_manda_el_audio_con_extension_idioma_modelo_y_prompt() -> None:
    transcriber = _make_transcriber()
    create = AsyncMock(return_value=_FakeTranscription("hola"))
    transcriber._client.audio.transcriptions.create = create

    await transcriber.transcribe(b"audio", audio_format=AudioFormat.M4A, language="es")

    create.assert_awaited_once_with(
        model="gpt-4o-mini-transcribe",
        file=("audio.m4a", b"audio"),
        language="es",
        prompt=TRANSCRIPTION_PROMPT,
    )


async def test_timeout_lanza_model_unavailable() -> None:
    transcriber = _make_transcriber()
    transcriber._client.audio.transcriptions.create = AsyncMock(
        side_effect=openai.APITimeoutError(request=httpx2.Request("POST", _URL))
    )

    with pytest.raises(ModelUnavailableError):
        await _transcribe(transcriber)


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (openai.RateLimitError, 429),
        (openai.AuthenticationError, 401),
        (openai.InternalServerError, 500),
        (openai.APIStatusError, 503),
    ],
)
async def test_errores_del_proveedor_lanzan_model_unavailable(
    error: type[openai.APIStatusError], status_code: int
) -> None:
    transcriber = _make_transcriber()
    transcriber._client.audio.transcriptions.create = AsyncMock(side_effect=_status_error(error, status_code))

    with pytest.raises(ModelUnavailableError):
        await _transcribe(transcriber)


async def test_audio_rechazado_por_el_proveedor_lanza_audio_not_understood() -> None:
    transcriber = _make_transcriber()
    transcriber._client.audio.transcriptions.create = AsyncMock(
        side_effect=_status_error(openai.BadRequestError, 400)
    )

    with pytest.raises(AudioNotUnderstoodError):
        await _transcribe(transcriber)


async def test_error_4xx_no_mapeado_se_propaga_tal_cual() -> None:
    transcriber = _make_transcriber()
    transcriber._client.audio.transcriptions.create = AsyncMock(
        side_effect=_status_error(openai.NotFoundError, 404)
    )

    with pytest.raises(openai.NotFoundError):
        await _transcribe(transcriber)


async def test_stub_devuelve_un_texto_fijo() -> None:
    transcriber = StubTranscriber(model="gpt-4o-mini-transcribe")

    assert await transcriber.transcribe(b"", audio_format=AudioFormat.OGG, language="es") == STUB_TRANSCRIPT


def test_build_transcriber_usa_el_stub_por_defecto() -> None:
    transcriber = build_transcriber(Settings(transcription_provider="stub"))

    assert isinstance(transcriber, StubTranscriber)


def test_build_transcriber_usa_openai_cuando_se_configura() -> None:
    settings = Settings(transcription_provider="openai", transcription_api_key="sk-test")

    transcriber = build_transcriber(settings)

    assert isinstance(transcriber, OpenAiTranscriber)


def test_openai_sin_api_key_no_levanta() -> None:
    with pytest.raises(ValidationError):
        Settings(transcription_provider="openai", transcription_api_key="")
