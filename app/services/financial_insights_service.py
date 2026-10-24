import logging

from app.infrastructure.llm.client import LlmClient
from app.infrastructure.prompts.financial_insights import (
    RESPONSE_SCHEMA,
    build_system_prompt,
    build_user_message,
)
from app.schemas.financial_insights import RecommendationsRequest, RecommendationsResponse
from app.services.recommendation_parsing import parse_recommendations

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

        return RecommendationsResponse(
            recommendations=parse_recommendations(raw),
            model=getattr(self._llm, "model", "unknown"),
        )
