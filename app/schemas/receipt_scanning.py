from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.enums import Currency, ExpenseCategory, PaymentMethod

MAX_MERCHANT_LENGTH = 100


class ReceiptScanStatus(StrEnum):
    PARSED = "parsed"
    MISSING_AMOUNT = "missing_amount"
    UNREADABLE = "unreadable"


class ScannedReceipt(BaseModel):
    merchant: str | None = Field(
        default=None,
        max_length=MAX_MERCHANT_LENGTH,
        description="Nombre comercial corto del comercio, o null si el comprobante no lo dice.",
    )
    amount: Decimal = Field(gt=0, decimal_places=2, description="Total del comprobante, siempre positivo.")
    currency: Currency
    occurred_on: date | None = Field(default=None, description="Fecha del comprobante, si se pudo leer.")
    category: ExpenseCategory
    payment_method: PaymentMethod | None = Field(
        default=None, description="Medio de pago, solo si el comprobante lo dice."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confianza de la lectura: la menor entre monto, fecha y comercio.",
    )


class ScanReceiptResponse(BaseModel):
    status: ReceiptScanStatus
    receipt: ScannedReceipt | None = Field(default=None, description="Solo cuando status es 'parsed'.")
    model: str = Field(description="OCR y modelo que produjeron el resultado, para trazabilidad.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "parsed",
                    "receipt": {
                        "merchant": "Supermercado Día",
                        "amount": "1250.50",
                        "currency": "ARS",
                        "occurred_on": "2026-10-14",
                        "category": "alimentos",
                        "payment_method": "debit_card",
                        "confidence": 0.93,
                    },
                    "model": "textract-analyze-expense+claude-sonnet-5",
                }
            ]
        }
    }
