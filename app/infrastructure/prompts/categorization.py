"""Prompt y JSON Schema para el caso de uso de categorizacion.

Separado del cliente a proposito: `AnthropicLlmClient` no sabe que es una
`ExpenseCategory`, solo sabe mandar texto y forzar una forma de respuesta via
`response_schema`. Este modulo es el que conoce el dominio (las 10 categorias)
y arma tanto las instrucciones como el schema que las fuerza.
"""

import json
from typing import Any

from app.domain.enums import ExpenseCategory
from app.schemas.categorization import TransactionInput

RESULT_TOOL_NAME = "emit_categorized_transactions"

_CATEGORY_VALUES = [category.value for category in ExpenseCategory]

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Id del movimiento, igual al recibido en el prompt.",
                    },
                    "category": {"type": "string", "enum": _CATEGORY_VALUES},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
                "required": ["id", "category", "confidence"],
            },
        },
    },
    "required": ["results"],
}


def build_system_prompt() -> str:
    categorias = ", ".join(_CATEGORY_VALUES)
    return (
        "Sos un clasificador de movimientos financieros personales. "
        "Para cada movimiento que te pasen, elegi exactamente una categoria "
        f"de esta lista cerrada, tal cual esta escrita: {categorias}. "
        "No inventes categorias nuevas, no las traduzcas ni cambies el formato. "
        "Devolve un resultado por cada movimiento recibido, usando el mismo "
        "'id' que te llego, con un 'confidence' entre 0.0 y 1.0 que refleje "
        "que tan seguro estas de la categoria elegida."
    )


def build_user_message(transactions: list[TransactionInput]) -> str:
    payload = [
        {
            "id": str(transaction.id),
            "description": transaction.description,
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "occurred_on": transaction.occurred_on.isoformat(),
            "merchant": transaction.merchant,
        }
        for transaction in transactions
    ]
    return json.dumps({"transactions": payload}, ensure_ascii=False)
