from app.domain.enums import Currency, ExpenseCategory
from app.infrastructure.prompts.email_parsing import RESPONSE_SCHEMA, build_system_prompt
from app.schemas.email_parsing import EmailParsingStatus


def test_el_prompt_lista_las_categorias_de_gasto() -> None:
    prompt = build_system_prompt(Currency.ARS)

    for category in ExpenseCategory:
        assert category.value in prompt


def test_el_prompt_prohibe_inventar_el_monto_contempla_reenvios_y_excluye_transporte() -> None:
    prompt = build_system_prompt(Currency.ARS)

    assert "missing_amount" in prompt
    assert "Nunca inventes" in prompt
    assert "reenvio" in prompt
    assert "Naturgy" in prompt
    assert "Cabify" in prompt


def test_el_schema_solo_exige_el_status() -> None:
    assert RESPONSE_SCHEMA["required"] == ["status"]
    assert RESPONSE_SCHEMA["properties"]["status"]["enum"] == [status.value for status in EmailParsingStatus]


def test_el_ejemplo_del_schema_es_una_factura_valida() -> None:
    example = RESPONSE_SCHEMA["examples"][0]

    assert example["status"] == "bill"
    assert example["category"] in [category.value for category in ExpenseCategory]
