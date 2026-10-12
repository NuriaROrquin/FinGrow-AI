import logging
from pathlib import PurePath

from app.core.exceptions import AudioNotUnderstoodError, AudioTooLargeError, UnsupportedAudioError
from app.domain.enums import AudioFormat
from app.infrastructure.transcription.client import Transcriber
from app.schemas.transcription import TranscriptionResponse

logger = logging.getLogger(__name__)

_FORMATS_BY_CONTENT_TYPE = {
    "audio/ogg": AudioFormat.OGG,
    "audio/opus": AudioFormat.OGG,
    "application/ogg": AudioFormat.OGG,
    "audio/mpeg": AudioFormat.MP3,
    "audio/mp3": AudioFormat.MP3,
    "audio/mp4": AudioFormat.MP4,
    "video/mp4": AudioFormat.MP4,
    "audio/m4a": AudioFormat.M4A,
    "audio/x-m4a": AudioFormat.M4A,
    "audio/wav": AudioFormat.WAV,
    "audio/wave": AudioFormat.WAV,
    "audio/x-wav": AudioFormat.WAV,
    "audio/webm": AudioFormat.WEBM,
    "audio/flac": AudioFormat.FLAC,
    "audio/x-flac": AudioFormat.FLAC,
}


class TranscriptionService:
    def __init__(self, transcriber: Transcriber, max_audio_bytes: int, language: str) -> None:
        self._transcriber = transcriber
        self.max_audio_bytes = max_audio_bytes
        self._language = language

    async def transcribe(
        self, audio: bytes, *, content_type: str | None, filename: str | None
    ) -> TranscriptionResponse:
        if not audio:
            raise AudioNotUnderstoodError("El audio llego vacio.")

        if len(audio) > self.max_audio_bytes:
            raise AudioTooLargeError(f"El audio supera el maximo de {self.max_audio_bytes} bytes.")

        audio_format = self._format(content_type, filename)
        logger.info("Transcribiendo un audio %s de %d bytes", audio_format, len(audio))

        transcript = await self._transcriber.transcribe(
            audio, audio_format=audio_format, language=self._language
        )
        text = transcript.strip()

        if not text:
            raise AudioNotUnderstoodError("No se reconocio ninguna frase en el audio.")

        return TranscriptionResponse(text=text, language=self._language, model=self._transcriber.model)

    @staticmethod
    def _format(content_type: str | None, filename: str | None) -> AudioFormat:
        media_type = (content_type or "").split(";")[0].strip().lower()
        if media_type in _FORMATS_BY_CONTENT_TYPE:
            return _FORMATS_BY_CONTENT_TYPE[media_type]

        extension = PurePath(filename or "").suffix.removeprefix(".").lower()
        try:
            return AudioFormat(extension)
        except ValueError:
            received = media_type or extension or "desconocido"
            raise UnsupportedAudioError(f"El formato '{received}' no se puede transcribir.") from None
