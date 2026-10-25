from fastapi import APIRouter, status

from app.api.deps import CompanyInsightsServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.company_insights import CompanyRecommendationsRequest
from app.schemas.financial_insights import RecommendationsResponse

router = APIRouter(prefix="/company-insights", tags=["company-insights"])


@router.post(
    "/recommendations",
    response_model=RecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Genera recomendaciones para una empresa a partir de indicadores agregados de su plantilla",
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def recommend(
    request: CompanyRecommendationsRequest,
    service: CompanyInsightsServiceDep,
) -> RecommendationsResponse:
    return await service.recommend(request)
