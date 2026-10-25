"""Lectura tolerante de las recomendaciones que devuelve el modelo (HU-44 y HU-25).

El modelo no siempre respeta la forma pedida: a veces devuelve una lista, a veces la serializa
como texto o usa otras claves. Se rescatan las recomendaciones validas y se descartan las demas.
"""

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import InferenceFailedError
from app.infrastructure.prompts.recommendations import RECOMMENDATION_SLOTS
from app.schemas.financial_insights import (
    MAX_BODY_LENGTH,
    MAX_TITLE_LENGTH,
    RECOMMENDATION_COUNT,
    Recommendation,
    RecommendationAction,
)

logger = logging.getLogger(__name__)

_CODED_FIELDS = ("kind", "action")
_MAX_LOGGED_VALUE_LENGTH = 40


def parse_recommendations(raw: str, *, action: RecommendationAction | None = None) -> list[Recommendation]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InferenceFailedError("La respuesta del modelo no tiene el formato esperado.") from exc

    entries = _entries(payload)
    if entries is None:
        logger.warning(
            "El modelo devolvio una respuesta de tipo %s sin recomendaciones", type(payload).__name__
        )
        raise InferenceFailedError("La respuesta del modelo no tiene el formato esperado.")

    recommendations = [
        recommendation
        for recommendation in (_recommendation(entry, action) for entry in entries)
        if recommendation is not None
    ][:RECOMMENDATION_COUNT]

    if not recommendations:
        raise InferenceFailedError("El modelo no devolvio ninguna recomendacion valida.")

    return recommendations


def _entries(payload: Any) -> list[Any] | None:
    if isinstance(payload, str):
        payload = _decode(payload)

    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict) or not payload:
        return None

    if "kind" in payload or "title" in payload:
        return [payload]

    if "recommendations" in payload:
        return _entries(payload["recommendations"])

    slots = [payload[slot] for slot in RECOMMENDATION_SLOTS if slot in payload]
    if slots:
        return slots

    return list(payload.values())


def _decode(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _recommendation(entry: Any, action: RecommendationAction | None) -> Recommendation | None:
    if isinstance(entry, str):
        entry = _decode(entry)

    if not isinstance(entry, dict):
        return None

    title = entry.get("title")
    body = entry.get("body")

    try:
        return Recommendation(
            kind=entry.get("kind"),
            title=title.strip()[:MAX_TITLE_LENGTH] if isinstance(title, str) else "",
            body=body.strip()[:MAX_BODY_LENGTH] if isinstance(body, str) else "",
            action=action if action is not None else entry.get("action"),
        )
    except ValidationError as exc:
        logger.warning("Se descarto una recomendacion incompleta del modelo: %s", _invalid_fields(exc, entry))
        return None


def _invalid_fields(exc: ValidationError, entry: dict[str, Any]) -> str:
    fields = dict.fromkeys(str(error["loc"][0]) for error in exc.errors())
    return ", ".join(_describe_field(field, entry) for field in fields)


def _describe_field(field: str, entry: dict[str, Any]) -> str:
    if field not in entry:
        return f"{field} ausente"

    if field in _CODED_FIELDS:
        return f"{field}={repr(entry[field])[:_MAX_LOGGED_VALUE_LENGTH]}"

    return f"{field} vacio"
