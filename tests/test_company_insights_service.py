import json
from decimal import Decimal
from typing import Any

import pytest

from app.core.exceptions import InferenceFailedError
from app.infrastructure.prompts.company_insights import RESPONSE_SCHEMA
from app.schemas.company_insights import (
    CompanyRecommendationsRequest,
    ConcernSummary,
    FinancialConcern,
)
from app.schemas.financial_insights import RecommendationAction, RecommendationKind
from app.services.company_insights_service import CompanyInsightsService


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


def _request() -> CompanyRecommendationsRequest:
    return CompanyRecommendationsRequest(
        month="2026-09",
        measured_employees=10,
        concerns=[
            ConcernSummary(
                concern=FinancialConcern.THIN_CUSHION,
                affected_employees=4,
                evaluated_employees=10,
                percentage=Decimal(40),
            )
        ],
    )


def _entry(kind: str = "tip", action: str = "none") -> dict[str, Any]:
    return {"kind": kind, "title": "Hacé un taller", "body": "Muchos tienen poco colchón.", "action": action}


async def test_devuelve_las_recomendaciones_del_modelo_con_el_schema_de_empresa() -> None:
    payload = {"first": _entry("warning"), "second": _entry("positive"), "third": _entry()}
    llm = _FakeLlmClient(json.dumps(payload))

    response = await CompanyInsightsService(llm=llm).recommend(_request())

    assert response.model == "fake-model"
    assert [recommendation.kind for recommendation in response.recommendations] == [
        RecommendationKind.WARNING,
        RecommendationKind.POSITIVE,
        RecommendationKind.TIP,
    ]
    assert llm.response_schema is RESPONSE_SCHEMA
    assert json.loads(llm.prompt)["concerns"][0]["concern"] == "thin_cushion"
    assert "area de personas" in llm.system


async def test_una_recomendacion_con_pantalla_del_empleado_queda_sin_pantalla() -> None:
    payload = {"first": _entry(action="budgets"), "second": _entry(action="education")}
    llm = _FakeLlmClient(json.dumps(payload))

    response = await CompanyInsightsService(llm=llm).recommend(_request())

    assert [recommendation.action for recommendation in response.recommendations] == [
        RecommendationAction.NONE,
        RecommendationAction.NONE,
    ]


async def test_descarta_las_recomendaciones_invalidas() -> None:
    llm = _FakeLlmClient(json.dumps({"recommendations": [_entry(kind="otro"), _entry()]}))

    response = await CompanyInsightsService(llm=llm).recommend(_request())

    assert len(response.recommendations) == 1


async def test_sin_recomendaciones_validas_falla_la_inferencia() -> None:
    llm = _FakeLlmClient(json.dumps({"first": {"title": "Sin tipo"}}))

    with pytest.raises(InferenceFailedError):
        await CompanyInsightsService(llm=llm).recommend(_request())
