"""Endpoint de ejemplo: categorizacion de movimientos.

Sirve de molde para los que vengan. Fijate lo que NO hay aca: ni validacion
(la hace Pydantic), ni try/except (los maneja error_handlers.py), ni logica
(vive en el service). La ruta solo traduce HTTP <-> caso de uso.
"""

from fastapi import APIRouter, status

from app.api.deps import CategorizationServiceDep
from app.schemas.categorization import CategorizeRequest, CategorizeResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/categorization", tags=["categorization"])


@router.post(
    "/transactions",
    response_model=CategorizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Categoriza un lote de movimientos",
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def categorize_transactions(
    request: CategorizeRequest,
    service: CategorizationServiceDep,
) -> CategorizeResponse:
    return await service.categorize(request)
