import pytest

from app.core.exceptions import AudioNotUnderstoodError, AudioTooLargeError, UnsupportedAudioError
from app.domain.enums import AudioFormat
from app.services.transcription_service import TranscriptionService


class _FakeTranscriber:
    model = "fake-transcribe"

    def __init__(self, transcript: str = "gaste 2500 en el super") -> None:
        self.transcript = transcript
        self.calls: list[tuple[bytes, AudioFormat, str]] = []

    async def transcribe(self, audio: bytes, *, audio_format: AudioFormat, language: str) -> str:
        self.calls.append((audio, audio_format, language))
        return self.transcript


def _service(transcriber: _FakeTranscriber, max_audio_bytes: int = 1000) -> TranscriptionService:
    return TranscriptionService(transcriber=transcriber, max_audio_bytes=max_audio_bytes, language="es")


async def test_devuelve_el_texto_con_idioma_y_modelo() -> None:
    transcriber = _FakeTranscriber()

    response = await _service(transcriber).transcribe(b"audio", content_type="audio/ogg", filename=None)

    assert response.text == "gaste 2500 en el super"
    assert response.language == "es"
    assert response.model == "fake-transcribe"
    assert transcriber.calls == [(b"audio", AudioFormat.OGG, "es")]


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("audio/ogg; codecs=opus", AudioFormat.OGG),
        ("AUDIO/MPEG", AudioFormat.MP3),
        ("audio/x-m4a", AudioFormat.M4A),
        ("audio/wave", AudioFormat.WAV),
    ],
)
async def test_reconoce_el_formato_por_content_type(content_type: str, expected: AudioFormat) -> None:
    transcriber = _FakeTranscriber()

    await _service(transcriber).transcribe(b"audio", content_type=content_type, filename=None)

    assert transcriber.calls[0][1] is expected


async def test_sin_content_type_de_audio_usa_la_extension_del_archivo() -> None:
    transcriber = _FakeTranscriber()

    await _service(transcriber).transcribe(
        b"audio", content_type="application/octet-stream", filename="nota.WEBM"
    )

    assert transcriber.calls[0][1] is AudioFormat.WEBM


async def test_una_nota_de_voz_exportada_de_whatsapp_como_opus_se_manda_como_ogg() -> None:
    transcriber = _FakeTranscriber()

    await _service(transcriber).transcribe(
        b"audio", content_type="application/octet-stream", filename="PTT-20261011-WA0001.opus"
    )

    assert transcriber.calls[0][1] is AudioFormat.OGG


async def test_un_formato_que_el_proveedor_no_acepta_es_rechazado() -> None:
    transcriber = _FakeTranscriber()

    with pytest.raises(UnsupportedAudioError):
        await _service(transcriber).transcribe(b"audio", content_type="audio/amr", filename="nota.amr")

    assert transcriber.calls == []


async def test_un_audio_vacio_no_se_entiende() -> None:
    with pytest.raises(AudioNotUnderstoodError):
        await _service(_FakeTranscriber()).transcribe(b"", content_type="audio/ogg", filename=None)


async def test_un_audio_mas_grande_que_el_maximo_es_rechazado() -> None:
    transcriber = _FakeTranscriber()

    with pytest.raises(AudioTooLargeError):
        await _service(transcriber, max_audio_bytes=4).transcribe(
            b"audio", content_type="audio/ogg", filename=None
        )

    assert transcriber.calls == []


async def test_si_no_se_reconoce_ninguna_frase_el_audio_no_se_entiende() -> None:
    with pytest.raises(AudioNotUnderstoodError):
        await _service(_FakeTranscriber(transcript="  \n ")).transcribe(
            b"audio", content_type="audio/ogg", filename=None
        )


async def test_recorta_los_espacios_del_texto() -> None:
    response = await _service(_FakeTranscriber(transcript="  gaste 500 \n")).transcribe(
        b"audio", content_type="audio/ogg", filename=None
    )

    assert response.text == "gaste 500"
