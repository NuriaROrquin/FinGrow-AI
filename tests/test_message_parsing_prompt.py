from app.domain.enums import Currency, ExpenseCategory, IncomeCategory
from app.infrastructure.prompts.message_parsing import RESPONSE_SCHEMA, build_system_prompt
from app.schemas.message_parsing import MessageParsingStatus


def test_el_prompt_lista_las_categorias_de_gasto_y_de_ingreso() -> None:
    prompt = build_system_prompt(Currency.ARS)

    for category in [*ExpenseCategory, *IncomeCategory]:
        assert category.value in prompt


def test_el_prompt_prohibe_inventar_el_monto() -> None:
    prompt = build_system_prompt(Currency.ARS)

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
