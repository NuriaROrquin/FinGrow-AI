import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.core.exceptions import InferenceFailedError
from app.domain.enums import Currency
from app.schemas.financial_insights import (
    MAX_TITLE_LENGTH,
    MonthSummary,
    RecommendationAction,
    RecommendationKind,
    RecommendationsRequest,
)
from app.services.financial_insights_service import FinancialInsightsService


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


def _request() -> RecommendationsRequest:
    return RecommendationsRequest(
        currency=Currency.ARS,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 15),
        months=[
            MonthSummary(month="2026-10", income=Decimal(1000), expenses=Decimal(900), savings=Decimal(100))
        ],
    )


def _entry(kind: str = "tip", action: str = "budgets", title: str = "Revisa alimentos") -> dict[str, Any]:
    return {"kind": kind, "title": title, "body": "Gastaste mas que el mes pasado.", "action": action}


async def test_devuelve_las_recomendaciones_del_modelo() -> None:
    entries = [_entry("positive", "goals"), _entry(), _entry("warning")]
    llm = _FakeLlmClient(json.dumps({"recommendations": entries}))

    response = await FinancialInsightsService(llm=llm).recommend(_request())

    assert response.model == "fake-model"
    assert [recommendation.kind for recommendation in response.recommendations] == [
        RecommendationKind.POSITIVE,
        RecommendationKind.TIP,
        RecommendationKind.WARNING,
    ]
    assert response.recommendations[0].action is RecommendationAction.GOALS
    assert llm.response_schema is not None
    assert json.loads(llm.prompt)["currency"] == "ARS"


async def test_descarta_las_recomendaciones_invalidas_y_se_queda_con_las_validas() -> None:
    entries = [_entry(kind="inventado"), _entry(action="home"), {"kind": "tip"}, "texto", _entry()]

    llm = _FakeLlmClient(json.dumps({"recommendations": entries}))

    response = await FinancialInsightsService(llm=llm).recommend(_request())

    assert len(response.recommendations) == 1


async def test_acepta_la_lista_de_recomendaciones_serializada_como_texto() -> None:
    entries = [_entry("positive", "goals"), _entry(), _entry("warning")]
    llm = _FakeLlmClient(json.dumps({"recommendations": json.dumps(entries)}))

    response = await FinancialInsightsService(llm=llm).recommend(_request())

    assert len(response.recommendations) == 3


async def test_lee_las_recomendaciones_de_las_claves_fijas_en_orden() -> None:
    payload = {"third": _entry("tip"), "first": _entry("positive", "goals"), "second": _entry("warning")}

    response = await FinancialInsightsService(llm=_FakeLlmClient(json.dumps(payload))).recommend(_request())

    assert [recommendation.kind for recommendation in response.recommendations] == [
        RecommendationKind.POSITIVE,
        RecommendationKind.WARNING,
        RecommendationKind.TIP,
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"recommendations": {"0": _entry(), "1": _entry("warning"), "2": _entry("positive")}},
        {"recommendations": {"first": _entry(), "second": _entry("warning"), "third": _entry("positive")}},
        {"first": json.dumps(_entry()), "second": _entry("warning"), "third": _entry("positive")},
    ],
)
async def test_acepta_las_variantes_de_forma_que_devuelve_el_modelo(payload: dict[str, Any]) -> None:
    response = await FinancialInsightsService(llm=_FakeLlmClient(json.dumps(payload))).recommend(_request())

    assert len(response.recommendations) == 3


async def test_una_sola_recomendacion_suelta_tambien_sirve() -> None:
    llm = _FakeLlmClient(json.dumps({"recommendations": _entry("positive", "goals")}))

    response = await FinancialInsightsService(llm=llm).recommend(_request())

    assert response.recommendations[0].action is RecommendationAction.GOALS


async def test_nunca_devuelve_mas_de_tres() -> None:
    llm = _FakeLlmClient(json.dumps({"recommendations": [_entry() for _ in range(5)]}))

    response = await FinancialInsightsService(llm=llm).recommend(_request())

    assert len(response.recommendations) == 3


async def test_recorta_un_titulo_demasiado_largo() -> None:
    llm = _FakeLlmClient(json.dumps({"recommendations": [_entry(title="  " + "a" * 200)]}))

    response = await FinancialInsightsService(llm=llm).recommend(_request())

    assert response.recommendations[0].title == "a" * MAX_TITLE_LENGTH


@pytest.mark.parametrize(
    "raw",
    [
        "no es json",
        json.dumps([]),
        json.dumps({"otra_cosa": []}),
        json.dumps({"recommendations": []}),
        json.dumps({}),
        json.dumps({"recommendations": "no es una lista"}),
        json.dumps({"recommendations": json.dumps({"kind": "tip"})}),
        json.dumps({"recommendations": [{"kind": "tip", "title": "", "body": "", "action": "none"}]}),
    ],
)
async def test_una_respuesta_sin_recomendaciones_validas_es_un_error_de_inferencia(raw: str) -> None:
    with pytest.raises(InferenceFailedError):
        await FinancialInsightsService(llm=_FakeLlmClient(raw)).recommend(_request())
