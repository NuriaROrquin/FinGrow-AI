import json
from decimal import Decimal
from typing import Any

import pytest

from app.core.exceptions import InferenceFailedError
from app.domain.enums import Currency
from app.schemas.message_parsing import MAX_DESCRIPTION_LENGTH, MessageParsingStatus, ParseMessageRequest
from app.services.message_parsing_service import MessageParsingService


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


def _service(payload: dict[str, Any]) -> MessageParsingService:
    return MessageParsingService(llm=_FakeLlmClient(json.dumps(payload)))


def _request(
    text: str = "Gaste $500 en supermercado", currency: Currency = Currency.ARS
) -> ParseMessageRequest:
    return ParseMessageRequest(text=text, default_currency=currency)


_EXPENSE = {
    "status": "parsed",
    "type": "expense",
    "amount": 500,
    "currency": "ARS",
    "expense_category": "alimentos",
    "description": "Supermercado",
    "confidence": 0.9,
}


async def test_interpreta_un_gasto() -> None:
    response = await _service(_EXPENSE).parse(_request())

    assert response.status is MessageParsingStatus.PARSED
    assert response.model == "fake-model"
    transaction = response.transaction
    assert transaction is not None
    assert transaction.type == "expense"
    assert transaction.amount == Decimal("500.00")
    assert transaction.currency == "ARS"
    assert transaction.expense_category == "alimentos"
    assert transaction.income_category is None
    assert transaction.payment_method is None
    assert transaction.description == "Supermercado"


async def test_interpreta_un_ingreso_con_su_categoria_y_medio_de_pago() -> None:
    payload = {
        "status": "parsed",
        "type": "income",
        "amount": 10000,
        "income_category": "freelance",
        "description": "Freelance",
        "payment_method": "bank_transfer",
        "confidence": 0.85,
    }

    response = await _service(payload).parse(_request("Ingreso de $10000 por freelance, me transfirieron"))

    transaction = response.transaction
    assert transaction is not None
    assert transaction.type == "income"
    assert transaction.income_category == "freelance"
    assert transaction.expense_category is None
    assert transaction.payment_method == "bank_transfer"


async def test_sin_moneda_usa_la_moneda_por_defecto_del_request() -> None:
    payload = {key: value for key, value in _EXPENSE.items() if key != "currency"}

    response = await _service(payload).parse(_request(currency=Currency.USD))

    assert response.transaction is not None
    assert response.transaction.currency == "USD"


async def test_el_monto_se_redondea_a_centavos_y_queda_positivo() -> None:
    response = await _service({**_EXPENSE, "amount": -1500.505}).parse(_request())

    assert response.transaction is not None
    assert response.transaction.amount == Decimal("1500.51")


@pytest.mark.parametrize("amount", [None, 0, "", "mucho", True])
async def test_un_parsed_sin_monto_legible_se_convierte_en_missing_amount(amount: Any) -> None:
    payload = {**_EXPENSE, "amount": amount}

    response = await _service(payload).parse(_request("Gaste en el super"))

    assert response.status is MessageParsingStatus.MISSING_AMOUNT
    assert response.transaction is None


async def test_un_parsed_que_omite_el_monto_se_convierte_en_missing_amount() -> None:
    payload = {key: value for key, value in _EXPENSE.items() if key != "amount"}

    response = await _service(payload).parse(_request("Gaste en el super"))

    assert response.status is MessageParsingStatus.MISSING_AMOUNT


@pytest.mark.parametrize("status", ["missing_amount", "not_a_transaction", "multiple_transactions"])
async def test_los_status_que_no_son_parsed_no_traen_movimiento(status: str) -> None:
    response = await _service({"status": status, "amount": 500}).parse(_request())

    assert response.status == status
    assert response.transaction is None


async def test_sin_descripcion_usa_el_texto_recortado() -> None:
    text = "x" * (MAX_DESCRIPTION_LENGTH + 50)

    response = await _service({**_EXPENSE, "description": "  "}).parse(_request(text))

    assert response.transaction is not None
    assert response.transaction.description == "x" * MAX_DESCRIPTION_LENGTH


async def test_el_prompt_usa_la_moneda_por_defecto_y_el_texto_viaja_como_dato() -> None:
    llm = _FakeLlmClient(json.dumps(_EXPENSE))

    await MessageParsingService(llm=llm).parse(_request("Gaste 20 en el kiosco", currency=Currency.USD))

    assert llm.system is not None
    assert "usa USD" in llm.system
    assert json.loads(llm.prompt or "") == {"text": "Gaste 20 en el kiosco"}


@pytest.mark.parametrize(
    "payload",
    [
        {**_EXPENSE, "expense_category": None},
        {**_EXPENSE, "income_category": "salario"},
        {**_EXPENSE, "type": "income"},
        {**_EXPENSE, "expense_category": "inventada"},
        {**_EXPENSE, "type": "transferencia"},
        {**_EXPENSE, "currency": "JPY"},
        {**_EXPENSE, "payment_method": "cheque"},
        {**_EXPENSE, "confidence": 1.5},
        {key: value for key, value in _EXPENSE.items() if key != "confidence"},
    ],
)
async def test_un_movimiento_incoherente_lanza_inference_failed(payload: dict[str, Any]) -> None:
    with pytest.raises(InferenceFailedError):
        await _service(payload).parse(_request())


@pytest.mark.parametrize("raw", ["esto no es json", "[]", json.dumps({"status": "quien sabe"})])
async def test_una_respuesta_ilegible_lanza_inference_failed(raw: str) -> None:
    service = MessageParsingService(llm=_FakeLlmClient(raw))

    with pytest.raises(InferenceFailedError):
        await service.parse(_request())
