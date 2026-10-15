"""Armado de dependencias.

Es el equivalente a DependencyInjection.cs: el unico lugar donde se decide
como se construye cada pieza. Las rutas piden lo que necesitan con Depends()
y no saben como se fabrica.

Sobre ciclos de vida, que es donde mas se confunde quien viene de .NET:
- Una funcion con Depends() corre una vez por request => equivale a Scoped.
- No hay AddSingleton. El equivalente es crear el objeto una sola vez al
  arrancar (ver el lifespan de main.py) y guardarlo en app.state. Ahi va todo
  lo caro de construir: clientes HTTP, modelos de ML, conexiones.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.infrastructure.llm.client import LlmClient
from app.infrastructure.ocr.client import ReceiptReader
from app.infrastructure.transcription.client import Transcriber
from app.services.categorization_service import CategorizationService
from app.services.email_parsing_service import EmailParsingService
from app.services.financial_insights_service import FinancialInsightsService
from app.services.message_parsing_service import MessageParsingService
from app.services.receipt_scanning_service import ReceiptScanningService
from app.services.transcription_service import TranscriptionService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_llm_client(request: Request) -> LlmClient:
    """Devuelve el cliente creado al arrancar la app (singleton por proceso)."""
    return request.app.state.llm_client


LlmClientDep = Annotated[LlmClient, Depends(get_llm_client)]


def get_categorization_service(llm: LlmClientDep) -> CategorizationService:
    return CategorizationService(llm=llm)


CategorizationServiceDep = Annotated[CategorizationService, Depends(get_categorization_service)]


def get_message_parsing_service(llm: LlmClientDep) -> MessageParsingService:
    return MessageParsingService(llm=llm)


MessageParsingServiceDep = Annotated[MessageParsingService, Depends(get_message_parsing_service)]


def get_transcriber(request: Request) -> Transcriber:
    return request.app.state.transcriber


TranscriberDep = Annotated[Transcriber, Depends(get_transcriber)]


def get_transcription_service(transcriber: TranscriberDep, settings: SettingsDep) -> TranscriptionService:
    return TranscriptionService(
        transcriber=transcriber,
        max_audio_bytes=settings.transcription_max_audio_bytes,
        language=settings.transcription_language,
    )


TranscriptionServiceDep = Annotated[TranscriptionService, Depends(get_transcription_service)]


def get_email_parsing_service(llm: LlmClientDep) -> EmailParsingService:
    return EmailParsingService(llm=llm)


EmailParsingServiceDep = Annotated[EmailParsingService, Depends(get_email_parsing_service)]


def get_receipt_reader(request: Request) -> ReceiptReader:
    return request.app.state.receipt_reader


ReceiptReaderDep = Annotated[ReceiptReader, Depends(get_receipt_reader)]


def get_receipt_scanning_service(
    reader: ReceiptReaderDep, llm: LlmClientDep, settings: SettingsDep
) -> ReceiptScanningService:
    return ReceiptScanningService(reader=reader, llm=llm, max_document_bytes=settings.ocr_max_document_bytes)


ReceiptScanningServiceDep = Annotated[ReceiptScanningService, Depends(get_receipt_scanning_service)]


def get_financial_insights_service(llm: LlmClientDep) -> FinancialInsightsService:
    return FinancialInsightsService(llm=llm)


FinancialInsightsServiceDep = Annotated[FinancialInsightsService, Depends(get_financial_insights_service)]
