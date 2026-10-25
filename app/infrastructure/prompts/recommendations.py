"""Piezas que comparten los prompts que devuelven recomendaciones (HU-44, HU-25 y HU-64).

Los endpoints responden con la misma forma (`Recommendation`), asi que el schema de la
respuesta, los nombres legibles de las categorias y los idiomas viven en un solo lugar.
"""

from collections.abc import Sequence
from typing import Any

from app.domain.enums import ExpenseCategory, Language
from app.schemas.financial_insights import (
    MAX_BODY_LENGTH,
    MAX_TITLE_LENGTH,
    RecommendationAction,
    RecommendationKind,
)

KIND_VALUES = [kind.value for kind in RecommendationKind]

CATEGORY_NAMES = {
    ExpenseCategory.ALIMENTOS: "alimentos",
    ExpenseCategory.TRANSPORTE: "transporte",
    ExpenseCategory.VIVIENDA: "vivienda",
    ExpenseCategory.SERVICIOS: "servicios",
    ExpenseCategory.SALUD: "salud",
    ExpenseCategory.EDUCACION: "educación",
    ExpenseCategory.ENTRETENIMIENTO: "entretenimiento",
    ExpenseCategory.INDUMENTARIA: "indumentaria",
    ExpenseCategory.AHORRO_INVERSION: "ahorro e inversión",
    ExpenseCategory.OTROS: "otros gastos",
}

LANGUAGES = {
    Language.ES: "castellano rioplatense, tuteando con voseo (vos tenés, revisá)",
    Language.EN: "English",
    Language.PT: "portugues do Brasil",
}

# Claves fijas en lugar de una lista: con una lista el modelo a veces devolvia menos elementos o
# la serializaba como texto.
RECOMMENDATION_SLOTS = ("first", "second", "third")


def _recommendation_schema(actions: Sequence[RecommendationAction]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": KIND_VALUES},
            "title": {"type": "string", "maxLength": MAX_TITLE_LENGTH},
            "body": {"type": "string", "maxLength": MAX_BODY_LENGTH},
            "action": {"type": "string", "enum": [action.value for action in actions]},
        },
        "required": ["kind", "title", "body", "action"],
    }


def category_list() -> str:
    return ", ".join(f"{category.value}: {name}" for category, name in CATEGORY_NAMES.items())


def response_schema(
    example: dict[str, dict[str, str]],
    actions: Sequence[RecommendationAction] = tuple(RecommendationAction),
) -> dict[str, Any]:
    """Schema de tres recomendaciones en `first`, `second` y `third`.

    El ejemplo es la respuesta que devuelve el stub cuando no hay modelo real. `actions` acota las
    pantallas a las que puede llevar una recomendacion: las de la empresa no llevan a ninguna.
    """
    recommendation = _recommendation_schema(actions)

    return {
        "type": "object",
        "properties": {slot: recommendation for slot in RECOMMENDATION_SLOTS},
        "required": list(RECOMMENDATION_SLOTS),
        "examples": [example],
    }
