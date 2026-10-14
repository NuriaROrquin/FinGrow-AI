from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import Currency, ExpenseCategory, IncomeCategory, PaymentMethod, TransactionType

MAX_TEXT_LENGTH = 1000
MAX_DESCRIPTION_LENGTH = 120


class MessageParsingStatus(StrEnum):
    PARSED = "parsed"
    MISSING_AMOUNT = "missing_amount"
    NOT_A_TRANSACTION = "not_a_transaction"
    MULTIPLE_TRANSACTIONS = "multiple_transactions"


class ParseMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    default_currency: Currency = Field(
        default=Currency.ARS,
        description="Moneda a usar cuando el mensaje no la menciona.",
    )
    today: date | None = Field(
        default=None,
        description="Fecha de hoy del empleado, contra la que se resuelven 'ayer' o 'el lunes'. "
        "Si no viene, se usa la de Argentina.",
    )


class ParsedTransaction(BaseModel):
    type: TransactionType
    amount: Decimal = Field(gt=0, decimal_places=2, description="Siempre positivo; el signo lo da `type`.")
    currency: Currency
    expense_category: ExpenseCategory | None = Field(default=None, description="Solo en gastos.")
    income_category: IncomeCategory | None = Field(default=None, description="Solo en ingresos.")
    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
    payment_method: PaymentMethod | None = Field(
        default=None,
        description="Null si el mensaje no lo dice: el backend se lo pregunta al empleado.",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Que tan segura es la categoria elegida.")
    occurred_on: date | None = Field(
        default=None,
        description="Null si el mensaje no dice la fecha: el backend usa la de hoy.",
    )
    occurred_on_is_estimate: bool = Field(
        default=False,
        description="True si el mensaje da un periodo vago ('la semana pasada') y la fecha es estimada.",
    )

    @model_validator(mode="after")
    def _category_matches_type(self) -> "ParsedTransaction":
        if self.type is TransactionType.EXPENSE and (
            self.expense_category is None or self.income_category is not None
        ):
            raise ValueError("Un gasto lleva categoria de gasto y ninguna de ingreso.")

        if self.type is TransactionType.INCOME and (
            self.income_category is None or self.expense_category is not None
        ):
            raise ValueError("Un ingreso lleva categoria de ingreso y ninguna de gasto.")

        return self


class ParseMessageResponse(BaseModel):
    status: MessageParsingStatus
    transaction: ParsedTransaction | None = Field(
        default=None,
        description="Solo cuando status es 'parsed'.",
    )
    model: str = Field(description="Modelo que produjo el resultado, para trazabilidad.")

    @model_validator(mode="after")
    def _transaction_only_when_parsed(self) -> "ParseMessageResponse":
        if (self.status is MessageParsingStatus.PARSED) != (self.transaction is not None):
            raise ValueError("Solo un mensaje interpretado como movimiento trae 'transaction'.")

        return self
