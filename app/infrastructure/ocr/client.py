import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings
from app.core.exceptions import (
    DocumentNotReadableError,
    DocumentTooLargeError,
    ModelUnavailableError,
    UnsupportedDocumentError,
)

logger = logging.getLogger(__name__)

TEXTRACT_MODEL = "textract-analyze-expense"
STUB_MODEL = "stub-ocr"

_VENDOR_TYPES = ("VENDOR_NAME", "NAME")
_TOTAL_TYPES = ("TOTAL", "AMOUNT_PAID", "AMOUNT_DUE")
_DATE_TYPES = ("INVOICE_RECEIPT_DATE",)
_MAX_ITEMS = 30

_UNAVAILABLE_CODES = {
    "ThrottlingException",
    "ProvisionedThroughputExceededException",
    "LimitExceededException",
    "InternalServerError",
    "ServiceUnavailableException",
}
_CREDENTIAL_CODES = {
    "AccessDeniedException",
    "UnrecognizedClientException",
    "InvalidSignatureException",
    "ExpiredTokenException",
}


@dataclass(frozen=True)
class OcrField:
    text: str
    confidence: float


@dataclass(frozen=True)
class ReceiptReading:
    vendor: OcrField | None = None
    total: OcrField | None = None
    receipt_date: OcrField | None = None
    items: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.vendor or self.total or self.receipt_date or self.items or self.lines)


class ReceiptReader(Protocol):
    model: str

    async def read(self, document: bytes) -> ReceiptReading: ...


class StubReceiptReader:
    def __init__(self) -> None:
        self.model = STUB_MODEL

    async def read(self, document: bytes) -> ReceiptReading:
        return ReceiptReading(
            vendor=OcrField("SUPERMERCADO DIA ARGENTINA S.A.", 0.97),
            total=OcrField("$ 1.250,50", 0.96),
            receipt_date=OcrField(date.today().strftime("%d/%m/%Y"), 0.93),
            items=["LECHE ENTERA 1L", "PAN LACTAL"],
            lines=["TOTAL $ 1.250,50", "TARJETA DE DEBITO"],
        )


class TextractReceiptReader:
    def __init__(
        self,
        *,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        timeout_seconds: int,
    ) -> None:
        self._client = boto3.client(
            "textract",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(
                connect_timeout=timeout_seconds,
                read_timeout=timeout_seconds,
                retries={"max_attempts": 2, "mode": "standard"},
            ),
        )
        self.model = TEXTRACT_MODEL

    async def read(self, document: bytes) -> ReceiptReading:
        try:
            response = await asyncio.to_thread(self._client.analyze_expense, Document={"Bytes": document})
        except ClientError as exc:
            raise self._translate(exc) from exc
        except BotoCoreError as exc:
            raise ModelUnavailableError("El proveedor de OCR no respondio a tiempo.") from exc

        return parse_analyze_expense(response)

    @staticmethod
    def _translate(exc: ClientError) -> Exception:
        code = exc.response.get("Error", {}).get("Code", "")

        if code == "DocumentTooLargeException":
            return DocumentTooLargeError("El comprobante es demasiado grande para el OCR.")
        if code == "UnsupportedDocumentException":
            return UnsupportedDocumentError(
                "El OCR no admite este documento: tiene que ser una imagen o un PDF de una sola pagina."
            )
        if code in {"BadDocumentException", "InvalidParameterException"}:
            return DocumentNotReadableError("El OCR no pudo leer el comprobante: puede estar danado.")
        if code in _CREDENTIAL_CODES:
            logger.error("Credenciales de OCR invalidas o sin permiso: %s", code)
            return ModelUnavailableError("El proveedor de OCR rechazo las credenciales.")
        if code in _UNAVAILABLE_CODES:
            return ModelUnavailableError("El proveedor de OCR no esta disponible en este momento.")

        logger.error("Error inesperado del proveedor de OCR: %s", code)
        return ModelUnavailableError("El proveedor de OCR respondio con un error.")


def parse_analyze_expense(response: dict[str, Any]) -> ReceiptReading:
    documents = response.get("ExpenseDocuments") or []
    if not documents:
        return ReceiptReading()

    document = documents[0]
    summary = document.get("SummaryFields") or []

    return ReceiptReading(
        vendor=_best_field(summary, _VENDOR_TYPES),
        total=_best_field(summary, _TOTAL_TYPES),
        receipt_date=_best_field(summary, _DATE_TYPES),
        items=_items(document.get("LineItemGroups") or []),
        lines=[
            block["Text"]
            for block in document.get("Blocks") or []
            if block.get("BlockType") == "LINE" and block.get("Text")
        ],
    )


def _best_field(fields: list[dict[str, Any]], types: tuple[str, ...]) -> OcrField | None:
    for field_type in types:
        candidates = [
            _to_field(entry)
            for entry in fields
            if entry.get("Type", {}).get("Text") == field_type
        ]
        candidates = [candidate for candidate in candidates if candidate is not None]
        if candidates:
            return max(candidates, key=lambda candidate: candidate.confidence)

    return None


def _to_field(entry: dict[str, Any]) -> OcrField | None:
    value = entry.get("ValueDetection") or {}
    text = (value.get("Text") or "").strip()
    if not text:
        return None

    return OcrField(text=text, confidence=_ratio(value.get("Confidence")))


def _items(groups: list[dict[str, Any]]) -> list[str]:
    items: list[str] = []
    for group in groups:
        for line_item in group.get("LineItems") or []:
            for entry in line_item.get("LineItemExpenseFields") or []:
                if entry.get("Type", {}).get("Text") != "ITEM":
                    continue
                text = ((entry.get("ValueDetection") or {}).get("Text") or "").strip()
                if text:
                    items.append(text)
                if len(items) >= _MAX_ITEMS:
                    return items

    return items


def _ratio(confidence: Any) -> float:
    try:
        value = float(confidence) / 100
    except (TypeError, ValueError):
        return 0.0

    return min(max(value, 0.0), 1.0)


def build_receipt_reader(settings: Settings) -> ReceiptReader:
    if settings.ocr_provider == "textract":
        return TextractReceiptReader(
            region=settings.ocr_aws_region,
            access_key_id=settings.ocr_aws_access_key_id,
            secret_access_key=settings.ocr_aws_secret_access_key,
            timeout_seconds=settings.ocr_timeout_seconds,
        )
    return StubReceiptReader()
