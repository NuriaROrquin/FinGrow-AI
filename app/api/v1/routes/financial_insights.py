from fastapi import APIRouter, status

from app.api.deps import FinancialInsightsServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.financial_insights import RecommendationsRequest, RecommendationsResponse

router = APIRouter(prefix="/financial-insights", tags=["financial-insights"])


@router.post(
    "/recommendations",
    response_model=RecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Genera recomendaciones accionables sobre el resumen financiero de un empleado",
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def recommend(
    request: RecommendationsRequest,
    service: FinancialInsightsServiceDep,
) -> RecommendationsResponse:
    return await service.recommend(request)
