import logging

from app.infrastructure.llm.client import LlmClient
from app.infrastructure.prompts.company_insights import (
    RESPONSE_SCHEMA,
    build_system_prompt,
    build_user_message,
)
from app.schemas.company_insights import CompanyRecommendationsRequest
from app.schemas.financial_insights import RecommendationAction, RecommendationsResponse
from app.services.recommendation_parsing import parse_recommendations

logger = logging.getLogger(__name__)


class CompanyInsightsService:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    async def recommend(self, request: CompanyRecommendationsRequest) -> RecommendationsResponse:
        logger.info("Generando recomendaciones para una empresa con %d preocupaciones", len(request.concerns))

        raw = await self._llm.complete(
            build_user_message(request),
            system=build_system_prompt(request),
            response_schema=RESPONSE_SCHEMA,
        )

        # El schema solo admite 'none', pero el modelo no siempre lo respeta: una recomendacion para
        # la empresa nunca lleva a una pantalla del empleado.
        recommendations = [
            recommendation.model_copy(update={"action": RecommendationAction.NONE})
            for recommendation in parse_recommendations(raw)
        ]

        return RecommendationsResponse(
            recommendations=recommendations,
            model=getattr(self._llm, "model", "unknown"),
        )
