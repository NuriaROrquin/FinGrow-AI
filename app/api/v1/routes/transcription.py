from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.api.deps import TranscriptionServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.transcription import TranscriptionResponse

router = APIRouter(prefix="/transcription", tags=["transcription"])


@router.post(
    "/audio",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe una nota de voz a texto",
    responses={
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def transcribe_audio(
    file: Annotated[UploadFile, File(description="Nota de voz en ogg, mp3, mp4, m4a, wav, webm o flac.")],
    service: TranscriptionServiceDep,
) -> TranscriptionResponse:
    audio = await file.read(service.max_audio_bytes + 1)

    return await service.transcribe(audio, content_type=file.content_type, filename=file.filename)
