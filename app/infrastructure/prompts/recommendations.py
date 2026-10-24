"""Piezas que comparten los prompts que devuelven recomendaciones (HU-44 y HU-25).

Los dos endpoints responden con la misma forma (`Recommendation`), asi que el schema de la
respuesta, los nombres legibles de las categorias y los idiomas viven en un solo lugar.
"""

from typing import Any

from app.domain.enums import ExpenseCategory, Language
from app.schemas.financial_insights import (
    MAX_BODY_LENGTH,
    MAX_TITLE_LENGTH,
    RecommendationAction,
    RecommendationKind,
)

KIND_VALUES = [kind.value for kind in RecommendationKind]
ACTION_VALUES = [action.value for action in RecommendationAction]

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

_RECOMMENDATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": KIND_VALUES},
        "title": {"type": "string", "maxLength": MAX_TITLE_LENGTH},
        "body": {"type": "string", "maxLength": MAX_BODY_LENGTH},
        "action": {"type": "string", "enum": ACTION_VALUES},
    },
    "required": ["kind", "title", "body", "action"],
}


def category_list() -> str:
    return ", ".join(f"{category.value}: {name}" for category, name in CATEGORY_NAMES.items())


def response_schema(example: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Schema de tres recomendaciones en `first`, `second` y `third`.

    El ejemplo es la respuesta que devuelve el stub cuando no hay modelo real.
    """
    return {
        "type": "object",
        "properties": {slot: _RECOMMENDATION_SCHEMA for slot in RECOMMENDATION_SLOTS},
        "required": list(RECOMMENDATION_SLOTS),
        "examples": [example],
    }
