import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.core.exceptions import (
    DocumentNotReadableError,
    DocumentTooLargeError,
    InferenceFailedError,
    UnsupportedDocumentError,
)
from app.domain.enums import Currency, ExpenseCategory, PaymentMethod
from app.infrastructure.ocr.client import OcrField, ReceiptReading
from app.schemas.receipt_scanning import ReceiptScanStatus
from app.services.receipt_scanning_service import MISSING_FIELD_CONFIDENCE, ReceiptScanningService

JPEG = b"\xff\xd8\xff\xe0receipt"
PNG = b"\x89PNG\r\n\x1a\nreceipt"
PDF = b"%PDF-1.7 receipt"


class _FakeReader:
    model = "fake-ocr"

    def __init__(self, reading: ReceiptReading) -> None:
        self.reading = reading
        self.calls: list[bytes] = []

    async def read(self, document: bytes) -> ReceiptReading:
        self.calls.append(document)
        return self.reading


class _FakeLlm:
    model = "fake-llm"

    def __init__(self, response: str | None = None) -> None:
        self.response = response or json.dumps({"merchant": "Supermercado Día", "category": "alimentos"})
        self.prompts: list[str] = []

    async def complete(
        self, prompt: str, *, system: str | None = None, response_schema: dict[str, Any] | None = None
    ) -> str:
        self.prompts.append(prompt)
        return self.response


def _reading(**overrides: Any) -> ReceiptReading:
    values: dict[str, Any] = {
        "vendor": OcrField("SUPERMERCADO DIA ARGENTINA S.A.", 0.98),
        "total": OcrField("$ 1.250,50", 0.95),
        "receipt_date": OcrField("14/10/2026", 0.9),
        "items": ["LECHE ENTERA 1L"],
        "lines": ["TOTAL $ 1.250,50", "TARJETA DE DEBITO", "CUIT 30-12345678-9"],
    }
    values.update(overrides)
    return ReceiptReading(**values)


def _service(
    reading: ReceiptReading | None = None, llm: _FakeLlm | None = None, max_document_bytes: int = 1000
) -> ReceiptScanningService:
    return ReceiptScanningService(
        reader=_FakeReader(reading or _reading()),
        llm=llm or _FakeLlm(),
        max_document_bytes=max_document_bytes,
    )


async def _scan(service: ReceiptScanningService, document: bytes = JPEG, content_type: str = "image/jpeg"):
    return await service.scan(
        document, content_type=content_type, filename=None, default_currency=Currency.ARS
    )


async def test_devuelve_comercio_monto_fecha_categoria_y_medio_de_pago() -> None:
    response = await _scan(_service())

    assert response.status is ReceiptScanStatus.PARSED
    assert response.model == "fake-ocr+fake-llm"
    receipt = response.receipt
    assert receipt is not None
    assert receipt.merchant == "Supermercado Día"
    assert receipt.amount == Decimal("1250.50")
    assert receipt.currency is Currency.ARS
    assert receipt.occurred_on == date(2026, 10, 14)
    assert receipt.category is ExpenseCategory.ALIMENTOS
    assert receipt.payment_method is PaymentMethod.DEBIT_CARD


async def test_la_confianza_es_la_menor_entre_monto_fecha_y_comercio() -> None:
    response = await _scan(_service())

    assert response.receipt is not None
    assert response.receipt.confidence == 0.9


async def test_sin_fecha_legible_la_confianza_no_puede_ser_alta() -> None:
    response = await _scan(_service(_reading(receipt_date=OcrField("sin fecha", 0.99))))

    assert response.receipt is not None
    assert response.receipt.occurred_on is None
    assert response.receipt.confidence == MISSING_FIELD_CONFIDENCE


async def test_al_modelo_solo_le_llegan_el_comercio_y_los_productos() -> None:
    llm = _FakeLlm()

    await _scan(_service(llm=llm))

    assert json.loads(llm.prompts[0]) == {
        "vendor": "SUPERMERCADO DIA ARGENTINA S.A.",
        "items": ["LECHE ENTERA 1L"],
    }


async def test_si_el_modelo_no_reconoce_el_comercio_queda_en_null() -> None:
    llm = _FakeLlm(json.dumps({"merchant": None, "category": "otros"}))

    response = await _scan(_service(_reading(vendor=None), llm=llm))

    assert response.receipt is not None
    assert response.receipt.merchant is None
    assert response.receipt.confidence == MISSING_FIELD_CONFIDENCE


async def test_detecta_la_moneda_en_el_total() -> None:
    response = await _scan(_service(_reading(total=OcrField("U$S 45,00", 0.95))))

    assert response.receipt is not None
    assert response.receipt.currency is Currency.USD


async def test_sin_total_legible_no_inventa_un_monto() -> None:
    llm = _FakeLlm()

    response = await _scan(_service(_reading(total=OcrField("TOTAL", 0.9)), llm=llm))

    assert response.status is ReceiptScanStatus.MISSING_AMOUNT
    assert response.receipt is None
    assert llm.prompts == []


async def test_un_comprobante_sin_ningun_texto_es_ilegible() -> None:
    response = await _scan(_service(ReceiptReading()))

    assert response.status is ReceiptScanStatus.UNREADABLE
    assert response.receipt is None


@pytest.mark.parametrize(("document", "content_type"), [(PNG, "image/png"), (PDF, "application/pdf")])
async def test_acepta_png_y_pdf(document: bytes, content_type: str) -> None:
    response = await _scan(_service(), document, content_type)

    assert response.status is ReceiptScanStatus.PARSED


async def test_sin_content_type_usa_la_extension() -> None:
    response = await _service().scan(
        JPEG, content_type="application/octet-stream", filename="ticket.JPG", default_currency=Currency.ARS
    )

    assert response.status is ReceiptScanStatus.PARSED


async def test_un_formato_que_el_ocr_no_acepta_es_rechazado() -> None:
    with pytest.raises(UnsupportedDocumentError):
        await _scan(_service(), b"RIFF....WEBP", "image/webp")


async def test_un_contenido_que_no_coincide_con_el_tipo_declarado_es_rechazado() -> None:
    with pytest.raises(UnsupportedDocumentError):
        await _scan(_service(), PNG, "image/jpeg")


async def test_un_comprobante_vacio_no_se_puede_leer() -> None:
    with pytest.raises(DocumentNotReadableError):
        await _scan(_service(), b"")


async def test_un_comprobante_mas_grande_que_el_maximo_no_llega_al_ocr() -> None:
    reader = _FakeReader(_reading())
    service = ReceiptScanningService(reader=reader, llm=_FakeLlm(), max_document_bytes=4)

    with pytest.raises(DocumentTooLargeError):
        await _scan(service)

    assert reader.calls == []


async def test_una_respuesta_del_modelo_que_no_es_json_falla_la_inferencia() -> None:
    with pytest.raises(InferenceFailedError):
        await _scan(_service(llm=_FakeLlm("no es json")))


async def test_una_categoria_fuera_del_contrato_falla_la_inferencia() -> None:
    llm = _FakeLlm(json.dumps({"merchant": "Kiosco", "category": "golosinas"}))

    with pytest.raises(InferenceFailedError):
        await _scan(_service(llm=llm))
