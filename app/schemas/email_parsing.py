from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.enums import Currency, ExpenseCategory

MAX_SUBJECT_LENGTH = 300
MAX_SENDER_LENGTH = 255
MAX_BODY_LENGTH = 8000
MAX_ISSUER_LENGTH = 60


class EmailParsingStatus(StrEnum):
    BILL = "bill"
    MISSING_AMOUNT = "missing_amount"
    NOT_A_BILL = "not_a_bill"


class ParseBillEmailRequest(BaseModel):
    subject: str = Field(default="", max_length=MAX_SUBJECT_LENGTH)
    sender: str = Field(
        default="",
        max_length=MAX_SENDER_LENGTH,
        description=(
            "Dominio o nombre del remitente, sin la direccion completa: en un reenvio es el empleado."
        ),
    )
    body: str = Field(
        min_length=1,
        max_length=MAX_BODY_LENGTH,
        description="Cuerpo del mail en texto plano. Un reenvio trae el remitente original dentro.",
    )
    default_currency: Currency = Field(
        default=Currency.ARS,
        description="Moneda a usar cuando el mail no la menciona.",
    )


class ParsedBill(BaseModel):
    issuer: str = Field(
        min_length=1,
        max_length=MAX_ISSUER_LENGTH,
        description="Nombre comercial corto de la empresa que factura ('Edenor', no 'EDENOR S.A.').",
    )
    amount: Decimal = Field(gt=0, decimal_places=2, description="Total a pagar, siempre positivo.")
    currency: Currency
    due_date: date | None = Field(default=None, description="Vencimiento, si el mail lo dice.")
    category: ExpenseCategory
    confidence: float = Field(ge=0.0, le=1.0, description="Que tan seguro es que el mail es una factura.")


class ParseBillEmailResponse(BaseModel):
    status: EmailParsingStatus
    bill: ParsedBill | None = Field(default=None, description="Solo cuando status es 'bill'.")
    model: str = Field(description="Modelo que produjo el resultado, para trazabilidad.")
