from fastapi import APIRouter, status

from app.api.deps import EmailParsingServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.email_parsing import ParseBillEmailRequest, ParseBillEmailResponse

router = APIRouter(prefix="/email-parsing", tags=["email-parsing"])


@router.post(
    "/bills",
    response_model=ParseBillEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Decide si un mail es una factura y extrae empresa, total, vencimiento y categoria",
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def parse_bill_email(
    request: ParseBillEmailRequest,
    service: EmailParsingServiceDep,
) -> ParseBillEmailResponse:
    return await service.parse_bill(request)
