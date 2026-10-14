from typing import Any
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    DocumentNotReadableError,
    DocumentTooLargeError,
    ModelUnavailableError,
    UnsupportedDocumentError,
)
from app.infrastructure.ocr.client import (
    STUB_MODEL,
    TEXTRACT_MODEL,
    OcrField,
    StubReceiptReader,
    TextractReceiptReader,
    build_receipt_reader,
    parse_analyze_expense,
)


def _summary(field_type: str, text: str, confidence: float) -> dict[str, Any]:
    return {
        "Type": {"Text": field_type, "Confidence": 99.0},
        "ValueDetection": {"Text": text, "Confidence": confidence},
    }


def _response() -> dict[str, Any]:
    return {
        "ExpenseDocuments": [
            {
                "SummaryFields": [
                    _summary("VENDOR_NAME", "FARMACITY S.A.", 97.5),
                    _summary("TOTAL", "$ 890,00", 80.0),
                    _summary("TOTAL", "$ 8.900,00", 96.0),
                    _summary("INVOICE_RECEIPT_DATE", "02/10/2026", 91.0),
                    _summary("TAX", "$ 154,46", 90.0),
                ],
                "LineItemGroups": [
                    {
                        "LineItems": [
                            {
                                "LineItemExpenseFields": [
                                    _summary("ITEM", "IBUPROFENO 400", 95.0),
                                    _summary("PRICE", "8900,00", 95.0),
                                ]
                            }
                        ]
                    }
                ],
                "Blocks": [
                    {"BlockType": "LINE", "Text": "FARMACITY"},
                    {"BlockType": "WORD", "Text": "FARMACITY"},
                    {"BlockType": "LINE", "Text": "TARJETA DE CREDITO"},
                ],
            }
        ]
    }


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, "AnalyzeExpense")


def _reader() -> TextractReceiptReader:
    return TextractReceiptReader(
        region="us-east-1", access_key_id="test", secret_access_key="test", timeout_seconds=5
    )


def test_toma_el_campo_de_mayor_confianza_de_cada_tipo() -> None:
    reading = parse_analyze_expense(_response())

    assert reading.vendor == OcrField("FARMACITY S.A.", 0.975)
    assert reading.total == OcrField("$ 8.900,00", 0.96)
    assert reading.receipt_date == OcrField("02/10/2026", 0.91)


def test_junta_los_productos_y_las_lineas_de_texto() -> None:
    reading = parse_analyze_expense(_response())

    assert reading.items == ["IBUPROFENO 400"]
    assert reading.lines == ["FARMACITY", "TARJETA DE CREDITO"]


def test_si_no_hay_total_usa_el_importe_pagado() -> None:
    response = {"ExpenseDocuments": [{"SummaryFields": [_summary("AMOUNT_PAID", "1500", 88.0)]}]}

    assert parse_analyze_expense(response).total == OcrField("1500", 0.88)


def test_sin_documentos_la_lectura_queda_vacia() -> None:
    assert parse_analyze_expense({"ExpenseDocuments": []}).is_empty


async def test_manda_el_documento_en_bytes_a_analyze_expense() -> None:
    reader = _reader()
    analyze = MagicMock(return_value=_response())
    reader._client.analyze_expense = analyze

    reading = await reader.read(b"documento")

    analyze.assert_called_once_with(Document={"Bytes": b"documento"})
    assert reading.total == OcrField("$ 8.900,00", 0.96)
    assert reader.model == TEXTRACT_MODEL


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("DocumentTooLargeException", DocumentTooLargeError),
        ("UnsupportedDocumentException", UnsupportedDocumentError),
        ("BadDocumentException", DocumentNotReadableError),
        ("InvalidParameterException", DocumentNotReadableError),
        ("ThrottlingException", ModelUnavailableError),
        ("AccessDeniedException", ModelUnavailableError),
        ("InternalServerError", ModelUnavailableError),
        ("SomethingNew", ModelUnavailableError),
    ],
)
async def test_traduce_los_errores_de_textract(code: str, expected: type[Exception]) -> None:
    reader = _reader()
    reader._client.analyze_expense = MagicMock(side_effect=_client_error(code))

    with pytest.raises(expected):
        await reader.read(b"documento")


async def test_si_textract_no_responde_el_ocr_no_esta_disponible() -> None:
    reader = _reader()
    reader._client.analyze_expense = MagicMock(
        side_effect=EndpointConnectionError(endpoint_url="https://textract.us-east-1.amazonaws.com")
    )

    with pytest.raises(ModelUnavailableError):
        await reader.read(b"documento")


def test_por_defecto_usa_el_stub() -> None:
    reader = build_receipt_reader(Settings())

    assert isinstance(reader, StubReceiptReader)
    assert reader.model == STUB_MODEL


def test_con_textract_arma_el_cliente_real() -> None:
    settings = Settings(
        ocr_provider="textract", ocr_aws_access_key_id="key", ocr_aws_secret_access_key="secret"
    )

    assert isinstance(build_receipt_reader(settings), TextractReceiptReader)


def test_textract_sin_credenciales_no_arranca() -> None:
    with pytest.raises(ValidationError):
        Settings(ocr_provider="textract")
