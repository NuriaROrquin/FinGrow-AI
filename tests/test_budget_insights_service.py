import json
from decimal import Decimal
from typing import Any

import pytest

from app.core.exceptions import InferenceFailedError
from app.domain.enums import Currency, ExpenseCategory
from app.infrastructure.prompts.budget_insights import RESPONSE_SCHEMA
from app.schemas.budget_insights import BudgetCategoryUsage, BudgetMonth, BudgetRecommendationsRequest
from app.schemas.financial_insights import RecommendationAction, RecommendationKind
from app.services.budget_insights_service import BudgetInsightsService


class _FakeLlmClient:
    model = "fake-model"

    def __init__(self, response: str) -> None:
        self._response = response
        self.system: str | None = None
        self.prompt: str | None = None
        self.response_schema: dict[str, Any] | None = None

    async def complete(
        self, prompt: str, *, system: str | None = None, response_schema: dict[str, Any] | None = None
    ) -> str:
        self.prompt = prompt
        self.system = system
        self.response_schema = response_schema
        return self._response

    async def is_available(self) -> bool:
        return True


def _request() -> BudgetRecommendationsRequest:
    return BudgetRecommendationsRequest(
        currency=Currency.ARS,
        months=[
            BudgetMonth(
                month="2026-09",
                limits=[
                    BudgetCategoryUsage(
                        category=ExpenseCategory.ALIMENTOS, limit=Decimal(100), spent=Decimal(130)
                    )
                ],
            )
        ],
    )


def _entry(kind: str = "tip", action: str = "budgets") -> dict[str, Any]:
    return {"kind": kind, "title": "Ajustá alimentos", "body": "Te pasaste del tope.", "action": action}


async def test_devuelve_las_recomendaciones_del_modelo_con_el_schema_de_presupuestos() -> None:
    payload = {"first": _entry("warning"), "second": _entry("positive", "goals"), "third": _entry()}
    llm = _FakeLlmClient(json.dumps(payload))

    response = await BudgetInsightsService(llm=llm).recommend(_request())

    assert response.model == "fake-model"
    assert [recommendation.kind for recommendation in response.recommendations] == [
        RecommendationKind.WARNING,
        RecommendationKind.POSITIVE,
        RecommendationKind.TIP,
    ]
    assert response.recommendations[1].action is RecommendationAction.GOALS
    assert llm.response_schema is RESPONSE_SCHEMA
    assert json.loads(llm.prompt)["months"][0]["limits"][0]["category"] == "alimentos"
    assert "presupuestos mensuales" in llm.system


async def test_descarta_las_recomendaciones_invalidas() -> None:
    llm = _FakeLlmClient(json.dumps({"recommendations": [_entry(kind="otro"), _entry()]}))

    response = await BudgetInsightsService(llm=llm).recommend(_request())

    assert len(response.recommendations) == 1


@pytest.mark.parametrize("raw", ["no es json", json.dumps({}), json.dumps({"recommendations": []})])
async def test_una_respuesta_sin_recomendaciones_validas_es_un_error_de_inferencia(raw: str) -> None:
    with pytest.raises(InferenceFailedError):
        await BudgetInsightsService(llm=_FakeLlmClient(raw)).recommend(_request())
