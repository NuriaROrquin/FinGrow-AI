from fastapi import APIRouter, status

from app.api.deps import MessageParsingServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.message_parsing import ParseMessageRequest, ParseMessageResponse

router = APIRouter(prefix="/message-parsing", tags=["message-parsing"])


@router.post(
    "/transactions",
    response_model=ParseMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Interpreta un mensaje en lenguaje natural como un movimiento",
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def parse_transaction_message(
    request: ParseMessageRequest,
    service: MessageParsingServiceDep,
) -> ParseMessageResponse:
    return await service.parse(request)
