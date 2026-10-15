import json
import logging
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import InferenceFailedError
from app.infrastructure.llm.client import LlmClient
from app.infrastructure.prompts.financial_insights import (
    RECOMMENDATION_SLOTS,
    RESPONSE_SCHEMA,
    build_system_prompt,
    build_user_message,
)
from app.schemas.financial_insights import (
    MAX_BODY_LENGTH,
    MAX_TITLE_LENGTH,
    RECOMMENDATION_COUNT,
    Recommendation,
    RecommendationsRequest,
    RecommendationsResponse,
)

logger = logging.getLogger(__name__)


class FinancialInsightsService:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    async def recommend(self, request: RecommendationsRequest) -> RecommendationsResponse:
        logger.info("Generando recomendaciones sobre %d meses", len(request.months))

        raw = await self._llm.complete(
            build_user_message(request),
            system=build_system_prompt(request),
            response_schema=RESPONSE_SCHEMA,
        )
        recommendations = self._recommendations(raw)

        return RecommendationsResponse(
            recommendations=recommendations,
            model=getattr(self._llm, "model", "unknown"),
        )

    @classmethod
    def _recommendations(cls, raw: str) -> list[Recommendation]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InferenceFailedError("La respuesta del modelo no tiene el formato esperado.") from exc

        entries = cls._entries(payload)
        if entries is None:
            logger.warning(
                "El modelo devolvio una respuesta de tipo %s sin recomendaciones", type(payload).__name__
            )
            raise InferenceFailedError("La respuesta del modelo no tiene el formato esperado.")

        recommendations = [
            recommendation
            for recommendation in (cls._recommendation(entry) for entry in entries)
            if recommendation is not None
        ][:RECOMMENDATION_COUNT]

        if not recommendations:
            raise InferenceFailedError("El modelo no devolvio ninguna recomendacion valida.")

        return recommendations

    @classmethod
    def _entries(cls, payload: Any) -> list[Any] | None:
        if isinstance(payload, str):
            payload = cls._decode(payload)

        if isinstance(payload, list):
            return payload

        if not isinstance(payload, dict) or not payload:
            return None

        if "kind" in payload or "title" in payload:
            return [payload]

        if "recommendations" in payload:
            return cls._entries(payload["recommendations"])

        slots = [payload[slot] for slot in RECOMMENDATION_SLOTS if slot in payload]
        if slots:
            return slots

        return list(payload.values())

    @staticmethod
    def _decode(value: str) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    @classmethod
    def _recommendation(cls, entry: Any) -> Recommendation | None:
        if isinstance(entry, str):
            entry = cls._decode(entry)

        if not isinstance(entry, dict):
            return None

        title = entry.get("title")
        body = entry.get("body")

        try:
            return Recommendation(
                kind=entry.get("kind"),
                title=title.strip()[:MAX_TITLE_LENGTH] if isinstance(title, str) else "",
                body=body.strip()[:MAX_BODY_LENGTH] if isinstance(body, str) else "",
                action=entry.get("action"),
            )
        except ValidationError:
            logger.warning("Se descarto una recomendacion incompleta del modelo")
            return None
