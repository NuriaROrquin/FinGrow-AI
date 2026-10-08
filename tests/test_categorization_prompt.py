from app.domain.enums import ExpenseCategory
from app.infrastructure.prompts.categorization import RESPONSE_SCHEMA, build_system_prompt


def test_el_prompt_lista_todas_las_categorias() -> None:
    prompt = build_system_prompt()

    for category in ExpenseCategory:
        assert category.value in prompt


def test_el_prompt_explica_como_calibrar_la_confianza() -> None:
    prompt = build_system_prompt()

    assert "0.8" in prompt
    assert "0.5" in prompt


def test_el_schema_exige_confidence_entre_cero_y_uno() -> None:
    item = RESPONSE_SCHEMA["properties"]["results"]["items"]

    assert "confidence" in item["required"]
    assert item["properties"]["confidence"]["minimum"] == 0.0
    assert item["properties"]["confidence"]["maximum"] == 1.0
