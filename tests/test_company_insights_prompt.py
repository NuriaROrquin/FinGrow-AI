import json
from decimal import Decimal

from app.domain.enums import Language
from app.infrastructure.prompts.company_insights import (
    RECOMMENDATION_SLOTS,
    RESPONSE_SCHEMA,
    build_system_prompt,
    build_user_message,
)
from app.schemas.company_insights import (
    CompanyRecommendationsRequest,
    ConcernSummary,
    FinancialConcern,
)
from app.schemas.financial_insights import RECOMMENDATION_COUNT, RecommendationsResponse


def _request(language: Language = Language.ES) -> CompanyRecommendationsRequest:
    return CompanyRecommendationsRequest(
        language=language,
        month="2026-09",
        measured_employees=10,
        average_score=Decimal("58.4"),
        participation_rate=Decimal(80),
        concerns=[
            ConcernSummary(
                concern=FinancialConcern.BUDGET_OVERRUNS,
                affected_employees=3,
                evaluated_employees=6,
                percentage=Decimal(50),
            ),
            ConcernSummary(
                concern=FinancialConcern.LOW_SAVINGS,
                affected_employees=7,
                evaluated_employees=10,
                percentage=Decimal(70),
            ),
        ],
    )


def test_el_prompt_dice_el_mes_y_explica_cada_preocupacion() -> None:
    prompt = build_system_prompt(_request())

    assert "2026-09" in prompt
    for concern in FinancialConcern:
        assert f"{concern.value}:" in prompt


def test_el_prompt_prohibe_identificar_empleados() -> None:
    prompt = " ".join(build_system_prompt(_request()).split())

    assert "Nunca hables de una persona en particular" in prompt


def test_el_prompt_prohibe_recomendar_productos_financieros() -> None:
    prompt = build_system_prompt(_request())

    assert "No recomiendes productos ni instrumentos financieros" in prompt


def test_el_prompt_pide_responder_en_el_idioma_de_la_empresa() -> None:
    assert "English" in build_system_prompt(_request(Language.EN))
    assert "portugues do Brasil" in build_system_prompt(_request(Language.PT))
    assert "voseo" in build_system_prompt(_request(Language.ES))


def test_el_mensaje_ordena_las_preocupaciones_por_peso_y_no_lleva_el_idioma() -> None:
    message = json.loads(build_user_message(_request()))

    assert "language" not in message
    assert message["month"] == "2026-09"
    assert [concern["concern"] for concern in message["concerns"]] == ["low_savings", "budget_overruns"]


def test_el_mensaje_solo_lleva_agregados() -> None:
    message = json.loads(build_user_message(_request()))

    assert set(message) == {
        "month",
        "measured_employees",
        "average_score",
        "participation_rate",
        "concerns",
    }
    for concern in message["concerns"]:
        assert set(concern) == {"concern", "affected_employees", "evaluated_employees", "percentage"}


def test_un_campo_no_declarado_nunca_llega_al_modelo() -> None:
    payload = _request().model_dump(mode="json")
    payload["employee_ids"] = ["0193a1b2-0000-7000-8000-000000000001"]
    payload["concerns"][0]["employee_ids"] = ["0193a1b2-0000-7000-8000-000000000002"]

    message = build_user_message(CompanyRecommendationsRequest.model_validate(payload))

    assert "employee_ids" not in message
    assert "0193a1b2" not in message


def test_el_schema_solo_admite_recomendaciones_sin_pantalla() -> None:
    for slot in RECOMMENDATION_SLOTS:
        assert RESPONSE_SCHEMA["properties"][slot]["properties"]["action"]["enum"] == ["none"]


def test_el_schema_pide_tres_recomendaciones_en_claves_fijas() -> None:
    assert len(RECOMMENDATION_SLOTS) == RECOMMENDATION_COUNT
    assert RESPONSE_SCHEMA["required"] == list(RECOMMENDATION_SLOTS)
    assert "array" not in json.dumps(RESPONSE_SCHEMA)


def test_el_ejemplo_del_schema_es_una_respuesta_valida() -> None:
    example = RESPONSE_SCHEMA["examples"][0]

    response = RecommendationsResponse(
        model="stub", recommendations=[example[slot] for slot in RECOMMENDATION_SLOTS]
    )

    assert len(response.recommendations) == RECOMMENDATION_COUNT
