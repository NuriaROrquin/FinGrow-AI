import json
from decimal import Decimal

from app.domain.enums import Currency, ExpenseCategory, Language
from app.infrastructure.prompts.budget_insights import (
    RECOMMENDATION_SLOTS,
    RESPONSE_SCHEMA,
    build_system_prompt,
    build_user_message,
)
from app.schemas.budget_insights import BudgetCategoryUsage, BudgetMonth, BudgetRecommendationsRequest
from app.schemas.financial_insights import RECOMMENDATION_COUNT, RecommendationsResponse


def _month(month: str, *, is_current: bool = False) -> BudgetMonth:
    return BudgetMonth(
        month=month,
        is_current=is_current,
        limits=[
            BudgetCategoryUsage(category=ExpenseCategory.ALIMENTOS, limit=Decimal(100), spent=Decimal(120))
        ],
    )


def _request(language: Language = Language.ES) -> BudgetRecommendationsRequest:
    return BudgetRecommendationsRequest(
        language=language,
        currency=Currency.USD,
        months=[_month("2026-10", is_current=True), _month("2026-08"), _month("2026-09")],
    )


def test_el_prompt_dice_la_moneda_y_lista_las_categorias() -> None:
    prompt = build_system_prompt(_request())

    assert "USD" in prompt
    for category in ExpenseCategory:
        assert category.value in prompt


def test_el_prompt_explica_que_el_mes_en_curso_es_parcial() -> None:
    prompt = " ".join(build_system_prompt(_request()).split())

    assert "'is_current' en true todavia no termino" in prompt
    assert "Las conclusiones salen de los meses cerrados" in prompt


def test_el_prompt_aclara_que_pasarse_en_ahorro_no_es_un_exceso() -> None:
    prompt = " ".join(build_system_prompt(_request()).split())

    assert "ahorro_inversion es ahorro, no consumo" in prompt


def test_el_prompt_prohibe_recomendar_productos_financieros() -> None:
    prompt = build_system_prompt(_request())

    assert "No recomiendes productos ni instrumentos financieros" in prompt


def test_el_prompt_pide_responder_en_el_idioma_del_empleado() -> None:
    assert "English" in build_system_prompt(_request(Language.EN))
    assert "portugues do Brasil" in build_system_prompt(_request(Language.PT))
    assert "voseo" in build_system_prompt(_request(Language.ES))


def test_el_mensaje_ordena_los_meses_y_no_lleva_el_idioma() -> None:
    message = json.loads(build_user_message(_request()))

    assert "language" not in message
    assert message["currency"] == "USD"
    assert [month["month"] for month in message["months"]] == ["2026-08", "2026-09", "2026-10"]
    assert message["months"][-1]["is_current"] is True


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
