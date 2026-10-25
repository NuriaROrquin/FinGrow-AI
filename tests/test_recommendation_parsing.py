import json
import logging

import pytest

from app.core.exceptions import InferenceFailedError
from app.schemas.financial_insights import RecommendationAction
from app.services.recommendation_parsing import parse_recommendations


def _entry(**fields: str) -> dict[str, str]:
    return {"kind": "tip", "title": "Revisá tus gastos", "body": "Gastaste más en transporte.", **fields}


def test_el_action_fijo_se_aplica_antes_de_validar() -> None:
    payload = {"first": _entry(), "second": _entry(action="budgets")}

    recommendations = parse_recommendations(json.dumps(payload), action=RecommendationAction.NONE)

    assert [recommendation.action for recommendation in recommendations] == [
        RecommendationAction.NONE,
        RecommendationAction.NONE,
    ]


def test_sin_action_fijo_una_recomendacion_sin_action_se_descarta() -> None:
    payload = {"first": _entry(), "second": _entry(action="goals")}

    recommendations = parse_recommendations(json.dumps(payload))

    assert [recommendation.action for recommendation in recommendations] == [RecommendationAction.GOALS]


def test_el_aviso_de_descarte_dice_que_campo_fallo_sin_el_texto(caplog: pytest.LogCaptureFixture) -> None:
    payload = {"first": {"kind": "alerta", "title": "Texto que no se loguea", "body": ""}}

    with caplog.at_level(logging.WARNING, logger="app.services.recommendation_parsing"):
        with pytest.raises(InferenceFailedError):
            parse_recommendations(json.dumps(payload))

    message = caplog.records[0].getMessage()
    assert "kind='alerta'" in message
    assert "action ausente" in message
    assert "body vacio" in message
    assert "Texto que no se loguea" not in message
