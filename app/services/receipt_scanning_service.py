import json
import logging
from pathlib import PurePath
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import (
    DocumentNotReadableError,
    DocumentTooLargeError,
    InferenceFailedError,
    UnsupportedDocumentError,
)
from app.domain.enums import Currency, DocumentFormat
from app.infrastructure.llm.client import LlmClient
from app.infrastructure.ocr.client import OcrField, ReceiptReader, ReceiptReading
from app.infrastructure.prompts.receipt_scanning import (
    RESPONSE_SCHEMA,
    build_system_prompt,
    build_user_message,
)
from app.schemas.receipt_scanning import (
    MAX_MERCHANT_LENGTH,
    ReceiptScanStatus,
    ScannedReceipt,
    ScanReceiptResponse,
)
from app.services.receipt_text import (
    detect_currency,
    detect_payment_method,
    normalize,
    parse_amount,
    parse_date,
)

logger = logging.getLogger(__name__)

MISSING_FIELD_CONFIDENCE = 0.5

_FORMATS_BY_CONTENT_TYPE = {
    "image/jpeg": DocumentFormat.JPEG,
    "image/jpg": DocumentFormat.JPEG,
    "image/pjpeg": DocumentFormat.JPEG,
    "image/png": DocumentFormat.PNG,
    "application/pdf": DocumentFormat.PDF,
}

_FORMATS_BY_EXTENSION = {
    "jpg": DocumentFormat.JPEG,
    "jpeg": DocumentFormat.JPEG,
    "png": DocumentFormat.PNG,
    "pdf": DocumentFormat.PDF,
}

_SIGNATURES = {
    DocumentFormat.JPEG: b"\xff\xd8\xff",
    DocumentFormat.PNG: b"\x89PNG\r\n\x1a\n",
    DocumentFormat.PDF: b"%PDF-",
}


class ReceiptScanningService:
    def __init__(self, reader: ReceiptReader, llm: LlmClient, max_document_bytes: int) -> None:
        self._reader = reader
        self._llm = llm
        self.max_document_bytes = max_document_bytes

    async def scan(
        self,
        document: bytes,
        *,
        content_type: str | None,
        filename: str | None,
        default_currency: Currency,
    ) -> ScanReceiptResponse:
        if not document:
            raise DocumentNotReadableError("El comprobante llego vacio.")

        if len(document) > self.max_document_bytes:
            raise DocumentTooLargeError(
                f"El comprobante supera el maximo de {self.max_document_bytes} bytes que admite el OCR."
            )

        document_format = self._format(content_type, filename)
        if not document.startswith(_SIGNATURES[document_format]):
            raise UnsupportedDocumentError("El contenido del archivo no corresponde al tipo declarado.")

        logger.info("Leyendo un comprobante %s de %d bytes", document_format, len(document))

        reading = await self._reader.read(document)

        if reading.is_empty:
            return ScanReceiptResponse(status=ReceiptScanStatus.UNREADABLE, model=self._reader.model)

        amount = parse_amount(reading.total.text) if reading.total else None
        if amount is None:
            return ScanReceiptResponse(status=ReceiptScanStatus.MISSING_AMOUNT, model=self._reader.model)

        merchant, category = await self._classify(reading)
        occurred_on = parse_date(reading.receipt_date.text) if reading.receipt_date else None

        try:
            receipt = ScannedReceipt(
                merchant=merchant,
                amount=amount,
                currency=detect_currency(self._currency_texts(reading), default_currency),
                occurred_on=occurred_on,
                category=category,
                payment_method=detect_payment_method(reading.lines),
                confidence=self._confidence(
                    reading.total,
                    reading.receipt_date if occurred_on else None,
                    reading.vendor if merchant else None,
                ),
            )
        except ValidationError as exc:
            raise InferenceFailedError("El comprobante leido quedo incompleto o incoherente.") from exc

        return ScanReceiptResponse(
            status=ReceiptScanStatus.PARSED,
            receipt=receipt,
            model=f"{self._reader.model}+{getattr(self._llm, 'model', 'unknown')}",
        )

    async def _classify(self, reading: ReceiptReading) -> tuple[str | None, Any]:
        vendor = reading.vendor.text if reading.vendor else None
        raw = await self._llm.complete(
            build_user_message(vendor, reading.items),
            system=build_system_prompt(),
            response_schema=RESPONSE_SCHEMA,
        )

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InferenceFailedError("La respuesta del modelo no tiene el formato esperado.") from exc

        if not isinstance(payload, dict):
            raise InferenceFailedError("La respuesta del modelo no tiene el formato esperado.")

        merchant = payload.get("merchant")
        merchant = merchant.strip()[:MAX_MERCHANT_LENGTH] if isinstance(merchant, str) else None

        return merchant or None, payload.get("category")

    @staticmethod
    def _currency_texts(reading: ReceiptReading) -> list[str]:
        texts = [line for line in reading.lines if "total" in normalize(line)]
        if reading.total:
            texts.append(reading.total.text)
        return texts

    @staticmethod
    def _confidence(*fields: OcrField | None) -> float:
        return round(
            min(field.confidence if field else MISSING_FIELD_CONFIDENCE for field in fields),
            4,
        )

    @staticmethod
    def _format(content_type: str | None, filename: str | None) -> DocumentFormat:
        media_type = (content_type or "").split(";")[0].strip().lower()
        if media_type in _FORMATS_BY_CONTENT_TYPE:
            return _FORMATS_BY_CONTENT_TYPE[media_type]

        extension = PurePath(filename or "").suffix.removeprefix(".").lower()
        if extension in _FORMATS_BY_EXTENSION:
            return _FORMATS_BY_EXTENSION[extension]

        received = media_type or extension or "desconocido"
        raise UnsupportedDocumentError(
            f"El formato '{received}' no se puede escanear: tiene que ser JPG, PNG o PDF."
        )
