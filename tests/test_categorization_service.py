"""Tests de CategorizationService con un LlmClient fake (no el StubLlmClient)."""

import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from app.core.exceptions import InferenceFailedError
from app.schemas.categorization import CategorizeRequest, TransactionInput
from app.services.categorization_service import CategorizationService


class _FakeLlmClient:
    model = "fake-model"

    def __init__(self, response: str) -> None:
        self._response = response

    async def complete(
        self, prompt: str, *, system: str | None = None, response_schema: dict[str, Any] | None = None
    ) -> str:
        return self._response

    async def is_available(self) -> bool:
        return True


def _request() -> CategorizeRequest:
    return CategorizeRequest(
        transactions=[
            TransactionInput(
                id=uuid4(),
                description="Supermercado Coto",
                amount=Decimal("-15400.50"),
                occurred_on=date(2026, 8, 20),
                merchant="COTO CICSA",
            )
        ]
    )


async def test_categoriza_con_respuesta_valida() -> None:
    request = _request()
    transaction_id = request.transactions[0].id
    raw = json.dumps({"results": [{"id": str(transaction_id), "category": "alimentos", "confidence": 0.9}]})
    service = CategorizationService(llm=_FakeLlmClient(raw))

    response = await service.categorize(request)

    assert len(response.results) == 1
    assert response.results[0].id == transaction_id
    assert response.results[0].category == "alimentos"
    assert response.results[0].confidence == 0.9
    assert response.model == "fake-model"


async def test_json_invalido_lanza_inference_failed() -> None:
    service = CategorizationService(llm=_FakeLlmClient("esto no es json"))

    with pytest.raises(InferenceFailedError):
        await service.categorize(_request())


async def test_categoria_fuera_del_enum_lanza_inference_failed() -> None:
    request = _request()
    raw = json.dumps(
        {"results": [{"id": str(request.transactions[0].id), "category": "inventada", "confidence": 0.5}]}
    )
    service = CategorizationService(llm=_FakeLlmClient(raw))

    with pytest.raises(InferenceFailedError):
        await service.categorize(request)


async def test_falta_un_resultado_por_transaccion_lanza_inference_failed() -> None:
    raw = json.dumps({"results": []})
    service = CategorizationService(llm=_FakeLlmClient(raw))

    with pytest.raises(InferenceFailedError):
        await service.categorize(_request())
