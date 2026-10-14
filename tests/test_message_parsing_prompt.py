from datetime import date

from app.domain.enums import Currency, ExpenseCategory, IncomeCategory
from app.infrastructure.prompts.message_parsing import RESPONSE_SCHEMA, build_system_prompt
from app.schemas.message_parsing import MessageParsingStatus

_TODAY = date(2026, 10, 12)


def test_el_prompt_lista_las_categorias_de_gasto_y_de_ingreso() -> None:
    prompt = build_system_prompt(Currency.ARS, _TODAY)

    for category in [*ExpenseCategory, *IncomeCategory]:
        assert category.value in prompt


def test_el_prompt_prohibe_inventar_el_monto() -> None:
    prompt = build_system_prompt(Currency.ARS, _TODAY)

    assert "missing_amount" in prompt
    assert "Nunca inventes" in prompt


def test_el_schema_solo_exige_el_status() -> None:
    assert RESPONSE_SCHEMA["required"] == ["status"]
    assert RESPONSE_SCHEMA["properties"]["status"]["enum"] == [
        status.value for status in MessageParsingStatus
    ]


def test_el_ejemplo_del_schema_es_un_movimiento_valido() -> None:
    example = RESPONSE_SCHEMA["examples"][0]

    assert example["status"] == "parsed"
    assert example["expense_category"] in [category.value for category in ExpenseCategory]


def test_el_prompt_dice_la_fecha_de_hoy_y_su_dia_de_la_semana() -> None:
    prompt = build_system_prompt(Currency.ARS, _TODAY)

    assert "hoy es lunes 2026-10-12" in prompt
    assert "occurred_on" in prompt


def test_la_fecha_es_opcional_en_el_schema() -> None:
    assert "occurred_on" in RESPONSE_SCHEMA["properties"]
    assert "occurred_on" not in RESPONSE_SCHEMA["required"]
    assert "occurred_on_is_estimate" not in RESPONSE_SCHEMA["required"]


def test_el_prompt_explica_como_estimar_un_periodo_vago() -> None:
    prompt = build_system_prompt(Currency.ARS, _TODAY)

    assert "la semana pasada" in prompt
    assert "occurred_on_is_estimate" in prompt
