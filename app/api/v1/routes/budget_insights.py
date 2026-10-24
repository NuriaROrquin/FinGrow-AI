from fastapi import APIRouter, status

from app.api.deps import BudgetInsightsServiceDep
from app.schemas.budget_insights import BudgetRecommendationsRequest
from app.schemas.common import ErrorResponse
from app.schemas.financial_insights import RecommendationsResponse

router = APIRouter(prefix="/budget-insights", tags=["budget-insights"])


@router.post(
    "/recommendations",
    response_model=RecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Genera recomendaciones sobre como le fue a un empleado con sus presupuestos mensuales",
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def recommend(
    request: BudgetRecommendationsRequest,
    service: BudgetInsightsServiceDep,
) -> RecommendationsResponse:
    return await service.recommend(request)
