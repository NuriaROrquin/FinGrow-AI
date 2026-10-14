from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import ReceiptScanningServiceDep
from app.domain.enums import Currency
from app.schemas.common import ErrorResponse
from app.schemas.receipt_scanning import ScanReceiptResponse

router = APIRouter(prefix="/receipt-scanning", tags=["receipt-scanning"])


@router.post(
    "/receipts",
    response_model=ScanReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Lee un ticket o factura y extrae comercio, total, fecha, categoria y medio de pago",
    responses={
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def scan_receipt(
    file: Annotated[UploadFile, File(description="Comprobante en JPG, PNG o PDF de una pagina.")],
    service: ReceiptScanningServiceDep,
    default_currency: Annotated[Currency, Form()] = Currency.ARS,
) -> ScanReceiptResponse:
    document = await file.read(service.max_document_bytes + 1)

    return await service.scan(
        document,
        content_type=file.content_type,
        filename=file.filename,
        default_currency=default_currency,
    )
