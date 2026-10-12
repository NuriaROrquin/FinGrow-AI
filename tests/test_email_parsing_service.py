import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.core.exceptions import InferenceFailedError
from app.domain.enums import Currency
from app.schemas.email_parsing import EmailParsingStatus, ParseBillEmailRequest
from app.services.email_parsing_service import EmailParsingService

_BODY = """\
---------- Forwarded message ---------
De: Edenor <facturas@edenor.com>
Consulta el detalle de tu factura.
TOTAL A PAGAR    $73.456,92
VENCIMIENTO    01/10/2026"""


class _FakeLlmClient:
    model = "fake-model"

    def __init__(self, response: str) -> None:
        self._response = response
        self.system: str | None = None
        self.prompt: str | None = None

    async def complete(
        self, prompt: str, *, system: str | None = None, response_schema: dict[str, Any] | None = None
    ) -> str:
        self.prompt = prompt
        self.system = system
        return self._response

    async def is_available(self) -> bool:
        return True


def _service(payload: dict[str, Any]) -> EmailParsingService:
    return EmailParsingService(llm=_FakeLlmClient(json.dumps(payload)))


def _request(body: str = _BODY, currency: Currency = Currency.ARS) -> ParseBillEmailRequest:
    return ParseBillEmailRequest(
        subject="Fwd: Tu factura", sender="gmail.com", body=body, default_currency=currency
    )


_BILL = {
    "status": "bill",
    "issuer": "Edenor",
    "amount": 73456.92,
    "currency": "ARS",
    "due_date": "2026-10-01",
    "category": "servicios",
    "confidence": 0.95,
}


async def test_interpreta_una_factura_reenviada() -> None:
    response = await _service(_BILL).parse_bill(_request())

    assert response.status is EmailParsingStatus.BILL
    assert response.model == "fake-model"
    bill = response.bill
    assert bill is not None
    assert bill.issuer == "Edenor"
    assert bill.amount == Decimal("73456.92")
    assert bill.currency == "ARS"
    assert bill.due_date == date(2026, 10, 1)
    assert bill.category == "servicios"


async def test_sin_moneda_usa_la_moneda_por_defecto_del_request() -> None:
    payload = {key: value for key, value in _BILL.items() if key != "currency"}

    response = await _service(payload).parse_bill(_request(currency=Currency.USD))

    assert response.bill is not None
    assert response.bill.currency == "USD"


@pytest.mark.parametrize("due_date", [None, "01/10/2026", "mañana", 20261001])
async def test_un_vencimiento_ilegible_no_invalida_la_factura(due_date: Any) -> None:
    response = await _service({**_BILL, "due_date": due_date}).parse_bill(_request())

    assert response.bill is not None
    assert response.bill.due_date is None


async def test_el_monto_se_redondea_a_centavos_y_queda_positivo() -> None:
    response = await _service({**_BILL, "amount": -1500.505}).parse_bill(_request())

    assert response.bill is not None
    assert response.bill.amount == Decimal("1500.51")


@pytest.mark.parametrize("amount", [None, 0, "", "mucho", True])
async def test_una_factura_sin_total_legible_se_convierte_en_missing_amount(amount: Any) -> None:
    response = await _service({**_BILL, "amount": amount}).parse_bill(_request())

    assert response.status is EmailParsingStatus.MISSING_AMOUNT
    assert response.bill is None


@pytest.mark.parametrize("status", ["missing_amount", "not_a_bill"])
async def test_los_status_que_no_son_bill_no_traen_factura(status: str) -> None:
    response = await _service({"status": status, "amount": 500}).parse_bill(_request())

    assert response.status == status
    assert response.bill is None


async def test_el_mail_viaja_como_dato_y_el_prompt_usa_la_moneda_por_defecto() -> None:
    llm = _FakeLlmClient(json.dumps(_BILL))

    await EmailParsingService(llm=llm).parse_bill(_request(currency=Currency.USD))

    assert llm.system is not None
    assert "usa USD" in llm.system
    assert json.loads(llm.prompt or "") == {
        "subject": "Fwd: Tu factura",
        "sender": "gmail.com",
        "body": _BODY,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {**_BILL, "issuer": "  "},
        {key: value for key, value in _BILL.items() if key != "issuer"},
        {**_BILL, "category": "inventada"},
        {key: value for key, value in _BILL.items() if key != "category"},
        {**_BILL, "currency": "JPY"},
        {**_BILL, "confidence": 1.5},
        {key: value for key, value in _BILL.items() if key != "confidence"},
    ],
)
async def test_una_factura_incoherente_lanza_inference_failed(payload: dict[str, Any]) -> None:
    with pytest.raises(InferenceFailedError):
        await _service(payload).parse_bill(_request())


@pytest.mark.parametrize("raw", ["esto no es json", "[]", json.dumps({"status": "quien sabe"})])
async def test_una_respuesta_ilegible_lanza_inference_failed(raw: str) -> None:
    service = EmailParsingService(llm=_FakeLlmClient(raw))

    with pytest.raises(InferenceFailedError):
        await service.parse_bill(_request())
